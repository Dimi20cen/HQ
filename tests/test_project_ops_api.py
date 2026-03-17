import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import fastapi.templating as fastapi_templating
import starlette.templating as starlette_templating


class ProjectOpsApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["HQ_PROJECTS_PATH"] = os.path.join(self.tempdir.name, "projects.json")
        os.environ["HQ_PROJECTS_EXPORT_PATH"] = os.path.join(
            self.tempdir.name, "projects.generated.json"
        )
        os.environ["CONTROLLER_DB_PATH"] = os.path.join(self.tempdir.name, "tools.db")
        sys.modules["psutil"] = types.SimpleNamespace(
            pid_exists=lambda _pid: False,
            Process=lambda _pid: None,
            NoSuchProcess=Exception,
            AccessDenied=Exception,
        )
        self.prev_fastapi_jinja_templates = fastapi_templating.Jinja2Templates
        self.prev_starlette_jinja_templates = starlette_templating.Jinja2Templates

        class FakeTemplates:
            def __init__(self, *args, **kwargs):
                pass

            def TemplateResponse(self, *args, **kwargs):
                return {"template": args[0] if args else "", "context": kwargs}

        fastapi_templating.Jinja2Templates = FakeTemplates
        starlette_templating.Jinja2Templates = FakeTemplates

        import controller.db as controller_db
        import controller.projects_registry as projects_registry
        import controller.controller_main as controller_main

        importlib.reload(controller_db)
        self.registry = importlib.reload(projects_registry)
        self.main = importlib.reload(controller_main)

        self.registry.create_project(
            {
                "slug": "jobby",
                "title": "Jobby",
                "public_summary": "Private workflow app",
                "public_mode": "source",
                "primary_url": "",
                "repo_url": "https://example.com/jobby",
                "sort_order": 40,
                "linked_tools": [],
                "private_url": "http://100.124.230.107:3000",
                "deployment_host": "srv",
                "deployment_location": "Server laptop over Tailscale",
                "runtime_path": "/srv/stacks/jobby",
                "health_public_url": "https://auth.dimy.dev/health",
                "health_private_url": "http://100.124.230.107:8001/health",
                "deploy_command": "/usr/bin/bash /srv/stacks/jobby/bin/deploy.sh",
                "start_command": "docker compose up -d",
                "restart_command": "docker compose restart",
                "stop_command": "docker compose down",
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()
        os.environ.pop("HQ_PROJECTS_PATH", None)
        os.environ.pop("HQ_PROJECTS_EXPORT_PATH", None)
        os.environ.pop("CONTROLLER_DB_PATH", None)
        sys.modules.pop("psutil", None)
        fastapi_templating.Jinja2Templates = self.prev_fastapi_jinja_templates
        starlette_templating.Jinja2Templates = self.prev_starlette_jinja_templates

    def read_payload(self, response):
        if isinstance(response, dict):
            return response
        return json.loads(response.body.decode("utf-8"))

    def test_health_check_reports_summary(self):
        response_ok = Mock(status_code=200)

        with patch.object(self.main.requests, "get", return_value=response_ok) as get_mock:
            response = self.main.check_project_health("jobby")

        payload = self.read_payload(response)
        self.assertEqual(payload["summary"], "healthy")
        self.assertEqual(payload["checks"]["public"]["status"], "healthy")
        self.assertEqual(payload["checks"]["private"]["status"], "healthy")
        self.assertEqual(get_mock.call_count, 2)

    def test_project_action_runs_configured_command(self):
        completed = Mock(returncode=0, stdout="restarted\n", stderr="")

        with patch.object(self.main.subprocess, "run", return_value=completed) as run_mock:
            response = self.main.run_project_action("jobby", {"action": "restart"})

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "restart")
        self.assertEqual(payload["stdout"], "restarted\n")
        run_mock.assert_called_once()
        self.assertEqual(run_mock.call_args.kwargs["cwd"], "/srv/stacks/jobby")
        self.assertEqual(payload["cwd"], "/srv/stacks/jobby")

    def test_project_action_rejects_missing_command(self):
        self.registry.update_project("jobby", {"stop_command": ""})

        response = self.main.run_project_action("jobby", {"action": "stop"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("No stop command configured", self.read_payload(response)["detail"])

    def test_publish_project_catalog_returns_publish_payload(self):
        with patch.object(
            self.main,
            "publish_portfolio_catalog",
            return_value={
                "ok": True,
                "detail": "Published portfolio catalog to origin.",
                "repo_path": "/srv/stacks/dimy.dev",
                "branch": "main",
                "origin_url": "https://github.com/Dimi20cen/dimy.dev.git",
                "export_path": "/srv/stacks/dimy.dev/data/projects.generated.json",
                "export_relpath": "data/projects.generated.json",
                "hq_export_path": "/srv/stacks/hq/runtime/projects/projects.generated.json",
                "count": 3,
                "no_changes": False,
                "commit_sha": "abc123",
                "commit_message": "Update portfolio project catalog",
                "stdout": "ok",
                "stderr": "",
            },
        ):
            response = self.main.publish_project_catalog()

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(payload["export_relpath"], "data/projects.generated.json")

    def test_publish_project_catalog_returns_validation_error(self):
        with patch.object(
            self.main,
            "publish_portfolio_catalog",
            side_effect=self.main.ProjectValidationError("repo is dirty"),
        ):
            response = self.main.publish_project_catalog()

        self.assertEqual(response.status_code, 400)
        self.assertIn("repo is dirty", self.read_payload(response)["detail"])


if __name__ == "__main__":
    unittest.main()
