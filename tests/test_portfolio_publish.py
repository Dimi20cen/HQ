import importlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class PortfolioPublishTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.projects_path = self.root / "projects.json"
        self.hq_export_path = self.root / "projects.generated.json"
        self.repo_dir = self.root / "dimy.dev"
        self.origin_dir = self.root / "origin.git"
        self.export_path = self.repo_dir / "data" / "projects.generated.json"

        os.environ["HQ_PROJECTS_PATH"] = str(self.projects_path)
        os.environ["HQ_PROJECTS_EXPORT_PATH"] = str(self.hq_export_path)
        os.environ["HQ_PORTFOLIO_REPO_DIR"] = str(self.repo_dir)
        os.environ["HQ_PORTFOLIO_EXPORT_PATH"] = str(self.export_path)
        os.environ["HQ_PORTFOLIO_BRANCH"] = "main"

        self.origin_dir.mkdir(parents=True, exist_ok=True)
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self._git(self.origin_dir, "init", "--bare")
        self._git(self.repo_dir, "init", "-b", "main")
        self._git(self.repo_dir, "config", "user.name", "HQ Tests")
        self._git(self.repo_dir, "config", "user.email", "hq-tests@example.com")
        self._git(self.repo_dir, "remote", "add", "origin", str(self.origin_dir))
        (self.repo_dir / "data").mkdir(parents=True, exist_ok=True)
        self.export_path.write_text("[]\n", encoding="utf-8")
        self._git(self.repo_dir, "add", "--", "data/projects.generated.json")
        self._git(self.repo_dir, "commit", "-m", "Initial portfolio data")
        self._git(self.repo_dir, "push", "-u", "origin", "main")

        import controller.projects_registry as projects_registry
        import controller.portfolio_publish as portfolio_publish

        self.registry = importlib.reload(projects_registry)
        self.publisher = importlib.reload(portfolio_publish)
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
                "private_url": "",
                "deployment_host": "aws",
                "deployment_location": "Lightsail",
                "runtime_path": "/srv/apps/rentpredictor",
                "health_public_url": "",
                "health_private_url": "",
                "deploy_command": "",
                "start_command": "",
                "restart_command": "",
                "stop_command": "",
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()
        for key in (
            "HQ_PROJECTS_PATH",
            "HQ_PROJECTS_EXPORT_PATH",
            "HQ_PORTFOLIO_REPO_DIR",
            "HQ_PORTFOLIO_EXPORT_PATH",
            "HQ_PORTFOLIO_BRANCH",
        ):
            os.environ.pop(key, None)

    def _git(self, cwd: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    def test_publish_commits_and_pushes_catalog(self):
        result = self.publisher.publish_portfolio_catalog()

        self.assertTrue(result["ok"])
        self.assertFalse(result["no_changes"])
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["export_relpath"], "data/projects.generated.json")
        self.assertTrue(result["commit_sha"])

        exported = json.loads(self.export_path.read_text(encoding="utf-8"))
        self.assertEqual(exported[0]["slug"], "rentpredictor")
        self.assertIn("Update portfolio project catalog", self._git(self.repo_dir, "log", "--oneline", "-1"))
        self.assertEqual(
            self._git(self.repo_dir, "rev-parse", "HEAD"),
            self._git(self.origin_dir, "rev-parse", "main"),
        )

    def test_publish_returns_no_changes_when_catalog_is_current(self):
        first = self.publisher.publish_portfolio_catalog()
        second = self.publisher.publish_portfolio_catalog()

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertTrue(second["no_changes"])
        self.assertEqual(second["commit_sha"], "")

    def test_publish_pushes_existing_local_commit_when_repo_is_ahead(self):
        first = self.publisher.publish_portfolio_catalog()

        self.assertTrue(first["ok"])
        self.assertFalse(first["no_changes"])

        self._git(self.repo_dir, "commit", "--allow-empty", "-m", "Local-only commit")

        second = self.publisher.publish_portfolio_catalog()

        self.assertTrue(second["ok"])
        self.assertFalse(second["no_changes"])
        self.assertEqual(
            second["detail"],
            "Pushed previously committed portfolio catalog to origin.",
        )
        self.assertEqual(
            self._git(self.repo_dir, "rev-parse", "HEAD"),
            self._git(self.origin_dir, "rev-parse", "main"),
        )

    def test_publish_rejects_unrelated_dirty_repo(self):
        (self.repo_dir / "README.md").write_text("dirty\n", encoding="utf-8")

        with self.assertRaises(self.publisher.ProjectValidationError) as ctx:
            self.publisher.publish_portfolio_catalog()

        self.assertIn("unrelated changes", str(ctx.exception))

    def test_publish_allows_initial_untracked_export_directory(self):
        self._git(self.repo_dir, "reset", "--hard", "HEAD")
        self.export_path.unlink()
        self._git(self.repo_dir, "rm", "--cached", "--", "data/projects.generated.json")
        (self.repo_dir / "data").rmdir()

        result = self.publisher.publish_portfolio_catalog()

        self.assertTrue(result["ok"])
        self.assertFalse(result["no_changes"])
        self.assertEqual(
            self._git(self.repo_dir, "rev-parse", "HEAD"),
            self._git(self.origin_dir, "rev-parse", "main"),
        )


if __name__ == "__main__":
    unittest.main()
