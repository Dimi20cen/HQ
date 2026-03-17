import importlib
import os
import tempfile
import unittest


class HostsRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["HQ_HOSTS_PATH"] = os.path.join(self.tempdir.name, "hosts.json")
        os.environ["HQ_PROJECTS_PATH"] = os.path.join(self.tempdir.name, "projects.json")
        import controller.hosts_registry as hosts_registry
        import controller.projects_registry as projects_registry

        self.hosts_registry = importlib.reload(hosts_registry)
        self.projects_registry = importlib.reload(projects_registry)

    def tearDown(self):
        os.environ.pop("HQ_HOSTS_PATH", None)
        os.environ.pop("HQ_PROJECTS_PATH", None)
        self.tempdir.cleanup()

    def test_create_and_update_host(self):
        host = self.hosts_registry.create_host(
            {
                "slug": "desk",
                "title": "desk",
                "transport": "http",
                "runner_url": "http://100.64.0.9:8051",
                "runner_socket_path": "",
                "token_env_var": "HQ_ACTION_RUNNER_TOKEN_DESK",
                "location": "Workstation",
                "notes": "Remote tailscale runner",
            }
        )

        self.assertEqual(host["slug"], "desk")
        self.assertEqual(self.hosts_registry.get_host("desk")["runner_url"], "http://100.64.0.9:8051")

        updated = self.hosts_registry.update_host("desk", {"transport": "none"})
        self.assertEqual(updated["transport"], "none")
        self.assertEqual(updated["runner_url"], "")

    def test_http_host_requires_runner_url(self):
        with self.assertRaises(self.hosts_registry.ProjectValidationError):
            self.hosts_registry.create_host(
                {
                    "slug": "desk",
                    "title": "desk",
                    "transport": "http",
                    "runner_url": "",
                }
            )

    def test_http_host_requires_token_env_var(self):
        with self.assertRaises(self.hosts_registry.ProjectValidationError):
            self.hosts_registry.create_host(
                {
                    "slug": "desk",
                    "title": "desk",
                    "transport": "http",
                    "runner_url": "http://100.64.0.9:8051",
                    "token_env_var": "",
                }
            )

    def test_socket_host_requires_socket_path(self):
        with self.assertRaises(self.hosts_registry.ProjectValidationError):
            self.hosts_registry.create_host(
                {
                    "slug": "srv",
                    "title": "srv",
                    "transport": "socket",
                    "runner_socket_path": "",
                }
            )

    def test_list_hosts_sorted_by_title(self):
        self.hosts_registry.create_host({"slug": "srv", "title": "srv", "transport": "none"})
        self.hosts_registry.create_host({"slug": "desk", "title": "desk", "transport": "none"})

        hosts = self.hosts_registry.list_hosts()
        self.assertEqual([item["slug"] for item in hosts], ["desk", "srv"])

    def test_delete_host_rejects_dependent_projects(self):
        self.hosts_registry.create_host(
            {
                "slug": "desk",
                "title": "desk",
                "transport": "http",
                "runner_url": "http://100.64.0.9:8051",
                "token_env_var": "HQ_ACTION_RUNNER_TOKEN_DESK",
            }
        )
        self.projects_registry.create_project(
            {
                "slug": "sakura",
                "title": "Sakura",
                "public_summary": "App",
                "public_mode": "source",
                "primary_url": "",
                "repo_url": "https://example.com/sakura",
                "sort_order": 10,
                "linked_tools": [],
                "depends_on": [],
                "private_url": "",
                "deployment_host": "desk",
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

        with self.assertRaises(self.hosts_registry.ProjectValidationError):
            self.hosts_registry.delete_host("desk")


if __name__ == "__main__":
    unittest.main()
