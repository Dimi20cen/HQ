import importlib
import json
import os
import tempfile
import unittest


class ProjectRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.projects_path = os.path.join(self.tempdir.name, "projects.json")
        self.export_path = os.path.join(self.tempdir.name, "projects.generated.json")
        self.portfolio_export_path = os.path.join(self.tempdir.name, "portfolio.generated.json")
        self.hosts_path = os.path.join(self.tempdir.name, "hosts.json")
        os.environ["HQ_PROJECTS_PATH"] = self.projects_path
        os.environ["HQ_PROJECTS_EXPORT_PATH"] = self.export_path
        os.environ["HQ_PORTFOLIO_EXPORT_PATH"] = self.portfolio_export_path
        os.environ["HQ_HOSTS_PATH"] = self.hosts_path

        import controller.projects_registry as projects_registry
        import controller.hosts_registry as hosts_registry

        self.registry = importlib.reload(projects_registry)
        self.hosts_registry = importlib.reload(hosts_registry)
        self.hosts_registry.create_host(
            {
                "slug": "srv",
                "title": "srv",
                "transport": "socket",
                "runner_socket_path": "/app/runtime/action-runner.sock",
                "runner_url": "",
                "token_env_var": "HQ_ACTION_RUNNER_TOKEN",
                "location": "Server laptop",
                "notes": "",
            }
        )
        self.hosts_registry.create_host(
            {
                "slug": "aws",
                "title": "aws",
                "transport": "none",
                "runner_socket_path": "",
                "runner_url": "",
                "token_env_var": "",
                "location": "Lightsail",
                "notes": "",
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()
        os.environ.pop("HQ_PROJECTS_PATH", None)
        os.environ.pop("HQ_PROJECTS_EXPORT_PATH", None)
        os.environ.pop("HQ_PORTFOLIO_EXPORT_PATH", None)
        os.environ.pop("HQ_HOSTS_PATH", None)

    def test_create_project_with_ops_fields(self):
        project = self.registry.create_project(
            {
                "slug": "jobby",
                "title": "Jobby",
                "public_summary": "Private workflow app",
                "public_mode": "source",
                "primary_url": "",
                "repo_url": "https://example.com/jobby",
                "sort_order": 40,
                "linked_tools": ["jobber"],
                "depends_on": ["janus", "hermes", "janus"],
                "private_url": "http://100.124.230.107:3000",
                "deployment_host": "srv",
                "deployment_location": "Server laptop over Tailscale",
                "runtime_path": "/srv/stacks/jobby",
                "health_public_url": "",
                "health_private_url": "http://100.124.230.107:8001/health",
                "deploy_command": "/usr/bin/bash /srv/stacks/jobby/bin/deploy.sh",
                "start_command": "docker compose up -d",
                "restart_command": "docker compose restart",
                "stop_command": "docker compose down",
                "logs_command": "docker compose logs --tail 100",
            }
        )

        self.assertEqual(project["deployment_host"], "srv")
        self.assertEqual(project["private_url"], "http://100.124.230.107:3000")
        self.assertEqual(project["health_private_url"], "http://100.124.230.107:8001/health")
        self.assertEqual(project["restart_command"], "docker compose restart")
        self.assertEqual(project["logs_command"], "docker compose logs --tail 100")
        self.assertEqual(project["depends_on"], ["janus", "hermes"])

    def test_create_project_rejects_unknown_deployment_host(self):
        with self.assertRaises(self.registry.ProjectValidationError):
            self.registry.create_project(
                {
                    "slug": "bad-host",
                    "title": "Bad Host",
                    "public_summary": "Broken host reference",
                    "public_mode": "source",
                    "primary_url": "",
                    "repo_url": "https://example.com/bad-host",
                    "sort_order": 50,
                    "linked_tools": [],
                    "depends_on": [],
                    "private_url": "",
                    "deployment_host": "missing-host",
                    "deployment_location": "",
                    "runtime_path": "",
                    "health_public_url": "",
                    "health_private_url": "",
                    "deploy_command": "",
                    "start_command": "",
                    "restart_command": "",
                    "stop_command": "",
                    "logs_command": "",
                }
            )

    def test_export_keeps_public_fields_only(self):
        self.registry.create_project(
            {
                "slug": "rentpredictor",
                "title": "Rent Predictor",
                "public_summary": "Public ML app",
                "public_mode": "full",
                "primary_url": "https://rent-predictor.dimy.dev",
                "repo_url": "https://example.com/rentpredictor",
                "sort_order": 10,
                "linked_tools": [],
                "depends_on": [],
                "private_url": "http://100.64.0.1:8501",
                "deployment_host": "aws",
                "deployment_location": "Lightsail",
                "runtime_path": "/srv/apps/rentpredictor",
                "health_public_url": "https://rent-predictor.dimy.dev/health",
                "health_private_url": "http://127.0.0.1:8501/health",
                "deploy_command": "./scripts/deploy_vps.sh",
                "start_command": "docker compose up -d",
                "restart_command": "docker compose restart",
                "stop_command": "docker compose down",
                "logs_command": "docker compose logs --tail 100",
            }
        )

        result = self.registry.export_projects()

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["synced_paths"], [self.portfolio_export_path])
        with open(self.export_path, "r", encoding="utf-8") as fh:
            exported = json.load(fh)
        with open(self.portfolio_export_path, "r", encoding="utf-8") as fh:
            portfolio_export = json.load(fh)
        self.assertEqual(exported[0]["slug"], "rentpredictor")
        self.assertEqual(portfolio_export, exported)
        self.assertNotIn("private_url", exported[0])
        self.assertNotIn("deploy_command", exported[0])
        self.assertNotIn("health_private_url", exported[0])
        self.assertNotIn("depends_on", exported[0])
        self.assertNotIn("logs_command", exported[0])


if __name__ == "__main__":
    unittest.main()
