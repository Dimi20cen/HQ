import os
import tempfile
import unittest

from controller.hosts_registry import (
    ProjectValidationError,
    create_host,
    get_host,
    list_hosts,
    update_host,
)


class HostsRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["HQ_HOSTS_PATH"] = os.path.join(self.tempdir.name, "hosts.json")

    def tearDown(self):
        os.environ.pop("HQ_HOSTS_PATH", None)
        self.tempdir.cleanup()

    def test_create_and_update_host(self):
        host = create_host(
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
        self.assertEqual(get_host("desk")["runner_url"], "http://100.64.0.9:8051")

        updated = update_host("desk", {"transport": "none"})
        self.assertEqual(updated["transport"], "none")
        self.assertEqual(updated["runner_url"], "")

    def test_http_host_requires_runner_url(self):
        with self.assertRaises(ProjectValidationError):
            create_host(
                {
                    "slug": "desk",
                    "title": "desk",
                    "transport": "http",
                    "runner_url": "",
                }
            )

    def test_socket_host_requires_socket_path(self):
        with self.assertRaises(ProjectValidationError):
            create_host(
                {
                    "slug": "srv",
                    "title": "srv",
                    "transport": "socket",
                    "runner_socket_path": "",
                }
            )

    def test_list_hosts_sorted_by_title(self):
        create_host({"slug": "srv", "title": "srv", "transport": "none"})
        create_host({"slug": "desk", "title": "desk", "transport": "none"})

        hosts = list_hosts()
        self.assertEqual([item["slug"] for item in hosts], ["desk", "srv"])


if __name__ == "__main__":
    unittest.main()
