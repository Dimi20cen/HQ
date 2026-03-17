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
        os.environ["HQ_HOSTS_PATH"] = os.path.join(self.tempdir.name, "hosts.json")
        os.environ["CONTROLLER_DB_PATH"] = os.path.join(self.tempdir.name, "tools.db")
        os.environ.pop("HQ_ACTION_RUNNER_URL", None)
        os.environ.pop("HQ_ACTION_RUNNER_SOCKET_PATH", None)
        os.environ.pop("HQ_ACTION_RUNNER_TOKEN", None)
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
        import controller.hosts_registry as hosts_registry
        import controller.projects_registry as projects_registry
        import controller.controller_main as controller_main

        importlib.reload(controller_db)
        self.hosts_registry = importlib.reload(hosts_registry)
        self.registry = importlib.reload(projects_registry)
        self.main = importlib.reload(controller_main)

        self.hosts_registry.create_host(
            {
                "slug": "srv",
                "title": "srv",
                "transport": "none",
                "runner_url": "",
                "runner_socket_path": "",
                "token_env_var": "HQ_ACTION_RUNNER_TOKEN",
                "location": "Server laptop",
                "notes": "",
            }
        )
        self.hosts_registry.create_host(
            {
                "slug": "desk",
                "title": "desk",
                "transport": "none",
                "runner_url": "",
                "runner_socket_path": "",
                "token_env_var": "HQ_ACTION_RUNNER_TOKEN_DESK",
                "location": "Workstation",
                "notes": "",
            }
        )

        self.registry.create_project(
            {
                "slug": "janus",
                "title": "Janus",
                "public_summary": "Shared auth",
                "public_mode": "source",
                "primary_url": "",
                "repo_url": "https://example.com/janus",
                "sort_order": 30,
                "linked_tools": [],
                "depends_on": [],
                "private_url": "http://100.124.230.107:8100",
                "deployment_host": "srv",
                "deployment_location": "Server laptop",
                "runtime_path": "/srv/stacks/janus",
                "health_public_url": "https://auth.dimy.dev/health",
                "health_private_url": "http://100.124.230.107:8100/health",
                "deploy_command": "/usr/bin/bash /srv/stacks/janus/bin/deploy.sh",
                "start_command": "docker compose up -d",
                "restart_command": "docker compose restart",
                "stop_command": "docker compose down",
                "logs_command": "docker compose logs --tail 100",
            }
        )

        self.registry.create_project(
            {
                "slug": "hermes",
                "title": "Hermes",
                "public_summary": "AI gateway",
                "public_mode": "source",
                "primary_url": "",
                "repo_url": "https://example.com/hermes",
                "sort_order": 35,
                "linked_tools": [],
                "depends_on": [],
                "private_url": "http://100.124.230.107:8010",
                "deployment_host": "srv",
                "deployment_location": "Server laptop",
                "runtime_path": "/srv/stacks/hermes",
                "health_public_url": "",
                "health_private_url": "http://100.124.230.107:8010/health",
                "deploy_command": "/usr/bin/bash /srv/stacks/hermes/bin/deploy.sh",
                "start_command": "",
                "restart_command": "systemctl --user restart hermes.service",
                "stop_command": "",
                "logs_command": "journalctl --user -u hermes.service -n 100 --no-pager",
            }
        )

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
                "depends_on": ["janus", "hermes"],
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
                "logs_command": "docker compose logs --tail 100",
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()
        os.environ.pop("HQ_PROJECTS_PATH", None)
        os.environ.pop("HQ_PROJECTS_EXPORT_PATH", None)
        os.environ.pop("HQ_HOSTS_PATH", None)
        os.environ.pop("CONTROLLER_DB_PATH", None)
        os.environ.pop("HQ_ACTION_RUNNER_URL", None)
        os.environ.pop("HQ_ACTION_RUNNER_SOCKET_PATH", None)
        os.environ.pop("HQ_ACTION_RUNNER_TOKEN", None)
        os.environ.pop("HQ_ACTION_RUNNER_TOKEN_DESK", None)
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
        self.registry.update_project("jobby", {"deployment_host": ""})
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

    def test_project_logs_action_runs_configured_command(self):
        self.registry.update_project("hermes", {"deployment_host": ""})
        completed = Mock(returncode=0, stdout="recent logs\n", stderr="")

        with patch.object(self.main.subprocess, "run", return_value=completed) as run_mock:
            response = self.main.run_project_action("hermes", {"action": "logs"})

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "logs")
        self.assertIn("recent logs", payload["stdout"])
        self.assertEqual(run_mock.call_args.kwargs["cwd"], "/srv/stacks/hermes")

    def test_project_action_uses_host_runner_when_configured(self):
        self.hosts_registry.update_host(
            "srv",
            {
                "transport": "http",
                "runner_url": "http://runner.local:8051",
            },
        )
        os.environ["HQ_ACTION_RUNNER_TOKEN"] = "runner-token"

        runner_response = Mock(
            status_code=200,
            text=json.dumps(
                {
                    "ok": True,
                    "action": "restart",
                    "command": "docker compose restart",
                    "cwd": "/srv/stacks/jobby",
                    "exit_code": 0,
                    "stdout": "runner ok\n",
                    "stderr": "",
                    "detail": "Command completed successfully.",
                    "ran_at": "2026-03-17T13:00:00Z",
                }
            ),
        )

        with patch.object(self.main.requests, "post", return_value=runner_response) as post_mock:
            response = self.main.run_project_action("jobby", {"action": "restart"})

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stdout"], "runner ok\n")
        self.assertEqual(
            post_mock.call_args.args[0],
            "http://runner.local:8051/run",
        )
        self.assertEqual(
            post_mock.call_args.kwargs["headers"]["Authorization"],
            "Bearer runner-token",
        )
        self.assertEqual(
            post_mock.call_args.kwargs["json"]["cwd"],
            "/srv/stacks/jobby",
        )

    def test_project_action_uses_host_runner_socket_when_configured(self):
        self.hosts_registry.update_host(
            "srv",
            {
                "transport": "socket",
                "runner_socket_path": "/app/runtime/action-runner.sock",
            },
        )

        with patch.object(
            self.main,
            "_run_project_command_via_runner",
            return_value={
                "ok": True,
                "action": "logs",
                "command": "docker compose logs --tail 100",
                "cwd": "/srv/stacks/jobby",
                "exit_code": 0,
                "stdout": "runner socket ok\n",
                "stderr": "",
                "detail": "Command completed successfully.",
                "ran_at": "2026-03-17T13:00:00Z",
            },
        ) as via_runner_mock:
            response = self.main.run_project_action("jobby", {"action": "logs"})

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stdout"], "runner socket ok\n")
        via_runner_mock.assert_called_once()

    def test_project_action_uses_remote_host_token_env_var(self):
        self.registry.update_project("jobby", {"deployment_host": "desk"})
        self.hosts_registry.update_host(
            "desk",
            {
                "transport": "http",
                "runner_url": "http://100.64.0.9:8051",
            },
        )
        os.environ["HQ_ACTION_RUNNER_TOKEN_DESK"] = "desk-token"

        runner_response = Mock(
            status_code=200,
            text=json.dumps(
                {
                    "ok": True,
                    "action": "logs",
                    "command": "docker compose logs --tail 100",
                    "cwd": "/srv/stacks/jobby",
                    "exit_code": 0,
                    "stdout": "desk ok\n",
                    "stderr": "",
                    "detail": "Command completed successfully.",
                    "ran_at": "2026-03-17T13:00:00Z",
                }
            ),
        )

        with patch.object(self.main.requests, "post", return_value=runner_response) as post_mock:
            response = self.main.run_project_action("jobby", {"action": "logs"})

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stdout"], "desk ok\n")
        self.assertEqual(post_mock.call_args.kwargs["headers"]["Authorization"], "Bearer desk-token")

    def test_http_runner_without_configured_token_is_treated_as_unconfigured(self):
        self.hosts_registry.update_host(
            "desk",
            {
                "transport": "http",
                "runner_url": "http://100.64.0.9:8051",
            },
        )
        os.environ.pop("HQ_ACTION_RUNNER_TOKEN_DESK", None)

        self.assertIsNone(self.main._host_runner_config(self.hosts_registry.get_host("desk")))

    def test_get_hosts_returns_cached_runner_state(self):
        response = self.main.get_hosts()

        payload = self.read_payload(response)
        by_slug = {item["slug"]: item for item in payload["hosts"]}
        self.assertEqual(by_slug["srv"]["runner_snapshot"]["status"], "unconfigured")
        self.assertNotIn("local-runner", by_slug)

    def test_refresh_hosts_health_checks_runner(self):
        self.hosts_registry.update_host(
            "srv",
            {
                "transport": "http",
                "runner_url": "http://runner.local:8051",
            },
        )
        os.environ["HQ_ACTION_RUNNER_TOKEN"] = "runner-token"
        response_ok = Mock(status_code=200, text=json.dumps({"ok": True, "service": "hq-action-runner"}))

        with patch.object(self.main.requests, "get", return_value=response_ok) as get_mock:
            response = self.main.refresh_hosts_health()

        payload = self.read_payload(response)
        by_slug = {item["slug"]: item for item in payload["hosts"]}
        self.assertEqual(by_slug["srv"]["runner_snapshot"]["status"], "healthy")
        self.assertEqual(get_mock.call_args.args[0], "http://runner.local:8051/health")

    def test_project_action_rejects_missing_command(self):
        self.registry.update_project("jobby", {"stop_command": ""})

        response = self.main.run_project_action("jobby", {"action": "stop"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("No stop command configured", self.read_payload(response)["detail"])

    def test_project_action_rejects_host_without_runner(self):
        response = self.main.run_project_action("jobby", {"action": "logs"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("does not have a runner configured", self.read_payload(response)["detail"])

    def test_project_action_rejects_unknown_host(self):
        with self.assertRaises(self.registry.ProjectValidationError):
            self.registry.update_project("jobby", {"deployment_host": "missing-host"})

    def test_delete_host_rejects_projects_still_assigned(self):
        response = self.main.remove_host("srv")

        self.assertEqual(response.status_code, 400)
        self.assertIn("still reference it", self.read_payload(response)["detail"])

    def test_project_action_without_deployment_host_runs_locally(self):
        self.registry.update_project("jobby", {"deployment_host": ""})
        completed = Mock(returncode=0, stdout="local ok\n", stderr="")

        with patch.object(self.main.subprocess, "run", return_value=completed) as run_mock:
            response = self.main.run_project_action("jobby", {"action": "logs"})

        payload = self.read_payload(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stdout"], "local ok\n")
        self.assertEqual(run_mock.call_args.kwargs["cwd"], "/srv/stacks/jobby")

    def test_get_projects_returns_cached_unknown_state_without_refresh(self):
        response = self.main.get_projects()

        payload = self.read_payload(response)
        by_slug = {item["slug"]: item for item in payload["projects"]}
        self.assertEqual(by_slug["jobby"]["health_snapshot"]["summary"], "unknown")
        self.assertEqual(by_slug["jobby"]["dependency_snapshot"]["summary"], "unknown")
        self.assertEqual(by_slug["jobby"]["ops_summary"], "unknown")

    def test_refresh_projects_health_includes_health_and_dependency_state(self):
        self.hosts_registry.update_host(
            "srv",
            {
                "transport": "http",
                "runner_url": "http://runner.local:8051",
            },
        )
        os.environ["HQ_ACTION_RUNNER_TOKEN"] = "runner-token"
        responses = {
            "https://auth.dimy.dev/health": Mock(status_code=200),
            "http://100.124.230.107:8100/health": Mock(status_code=200),
            "http://100.124.230.107:8010/health": Mock(status_code=503),
            "http://100.124.230.107:8001/health": Mock(status_code=200),
            "http://runner.local:8051/health": Mock(
                status_code=200, text=json.dumps({"ok": True, "service": "hq-action-runner"})
            ),
        }

        def fake_get(url, timeout=5, **kwargs):
            return responses[url]

        with patch.object(self.main.requests, "get", side_effect=fake_get):
            response = self.main.refresh_projects_health()

        payload = self.read_payload(response)
        by_slug = {item["slug"]: item for item in payload["projects"]}
        self.assertEqual(by_slug["jobby"]["health_snapshot"]["summary"], "healthy")
        self.assertEqual(by_slug["jobby"]["dependency_snapshot"]["summary"], "down")
        self.assertEqual(by_slug["jobby"]["ops_summary"], "degraded")
        self.assertEqual(by_slug["jobby"]["host_snapshot"]["status"], "healthy")

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
