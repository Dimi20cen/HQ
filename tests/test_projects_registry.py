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
        os.environ["HQ_PROJECTS_PATH"] = self.projects_path
        os.environ["HQ_PROJECTS_EXPORT_PATH"] = self.export_path
        os.environ["HQ_PORTFOLIO_EXPORT_PATH"] = self.portfolio_export_path

        import controller.projects_registry as projects_registry

        self.registry = importlib.reload(projects_registry)

    def tearDown(self):
        self.tempdir.cleanup()
        os.environ.pop("HQ_PROJECTS_PATH", None)
        os.environ.pop("HQ_PROJECTS_EXPORT_PATH", None)
        os.environ.pop("HQ_PORTFOLIO_EXPORT_PATH", None)

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
