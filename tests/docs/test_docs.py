"""Verify the documentation site and the Pages publication boundary."""

import tomllib
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]


class Page(HTMLParser):
    """Collect rendered anchors and local resource references."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.feed(path.read_text())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record link targets and anchor IDs from generated HTML."""
        values = dict(attrs)
        if anchor := values.get("id"):
            self.anchors.add(anchor)
        for attribute in ("href", "src"):
            if link := values.get(attribute):
                self.links.append(link)


class DocumentationTests(unittest.TestCase):
    """Exercise rendered navigation and publishing configuration."""

    def test_cloudflare_build_tool_matches_lock(self) -> None:
        """Pages bootstraps the same generator as local isolated docs builds."""
        lock = tomllib.loads((ROOT / "uv.lock").read_text())
        version = next(p["version"] for p in lock["package"] if p["name"] == "zensical")
        requirements = [
            line.strip()
            for line in (ROOT / "src/frontend/requirements.txt")
            .read_text()
            .splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertEqual(requirements, [f"zensical=={version}"])
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertTrue(
            any(r.startswith("zensical") for r in project["build-system"]["requires"])
        )
        self.assertFalse(
            any(r.startswith("zensical") for r in project["project"]["dependencies"])
        )

    def test_pages_publishes_only_after_main_ci(self) -> None:
        """PRs build the docs; only successful main CI can publish them."""
        release = yaml.safe_load((ROOT / ".github/workflows/release.yaml").read_text())
        # YAML 1.1 interprets GitHub's unquoted `on` key as a boolean.
        triggers = release[True]
        self.assertEqual(triggers, {"push": {"branches": ["main"]}})
        deploy = release["jobs"]["docs"]
        self.assertIn("ci", deploy["needs"])
        self.assertEqual(deploy["if"], "github.repository == 'juftin/camply-web'")
        self.assertEqual(deploy["permissions"]["pages"], "write")
        self.assertEqual(deploy["permissions"]["id-token"], "write")
        self.assertEqual(deploy["environment"]["name"], "github-pages")
        self.assertEqual(
            deploy["environment"]["url"], "${{ steps.deployment.outputs.page_url }}"
        )
        publish = next(s for s in deploy["steps"] if s.get("id") == "deployment")
        config = tomllib.loads((ROOT / "zensical.toml").read_text())["project"]
        self.assertEqual(publish["with"]["path"], config["site_dir"])
        self.assertEqual(config["site_url"], "https://camply.juftin.dev/docs/")
        ci = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text())
        build = ci["jobs"]["docs"]["steps"][-1]
        self.assertEqual(build["with"]["task"], "docs:check")
        self.assertNotIn("pages", ci["permissions"])

    @unittest.skipUnless(
        (ROOT / "build/docs/index.html").exists(), "Run task docs:build first"
    )
    def test_rendered_links_and_assets(self) -> None:
        """Every generated page must have working local links and anchors."""
        directory = ROOT / "build/docs"
        pages = {path.resolve(): Page(path) for path in directory.rglob("*.html")}
        source = ROOT / "docs/zensical"
        for markdown in source.rglob("*.md"):
            route = markdown.relative_to(source).with_suffix("")
            target = directory / route / "index.html"
            if markdown.name == "index.md":
                target = directory / route.with_suffix(".html")
            self.assertTrue(target.is_file(), f"Missing built page for {markdown}")
        for path, page in pages.items():
            if path.name == "404.html":
                continue
            for link in page.links:
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                with self.subTest(page=path.relative_to(directory), link=link):
                    target = (path.parent / unquote(url.path)).resolve()
                    if not url.path:
                        target = path
                    if target.is_dir():
                        target /= "index.html"
                    self.assertTrue(target.is_file(), f"Missing target: {target}")
                    if url.fragment and target in pages:
                        self.assertIn(unquote(url.fragment), pages[target].anchors)


if __name__ == "__main__":
    unittest.main()
