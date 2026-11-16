"""Verify the documentation site and the Pages publication boundary."""

import json
import re
import tomllib
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "docs"

# Retired root-level doc paths replaced during the documentation rework.
RETIRED_DOCS = ("configuration.md", "development.md")

# Generic boilerplate opening phrases disallowed in active documentation.
BANNED_OPENER_PREFIXES = (
    "welcome to ",
    "thank you for your interest",
    "this document defines",
    "let's dive into",
)

# Match Markdown headings that begin with a decorative symbol or emoji.
_HEADING_EMOJI_PATTERN = re.compile(
    r"^#{1,6}\s+[^\w\s`\[(\"']",
)

# Match GitHub blob links targeting active pages already hosted on the docs site.
_INTERNAL_BLOB_LINK_PATTERN = re.compile(
    r"https://github\.com/juftin/camply-web/blob/main/docs/(?!specs/)[^\s)>\"']+"
)


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

    def test_documentation_tooling_and_dependencies(self) -> None:
        """VitePress and Mermaid are managed through package.json with no Python docs dependencies."""
        package = json.loads((ROOT / "package.json").read_text())
        self.assertIn("vitepress", package["devDependencies"])
        self.assertIn("mermaid", package["devDependencies"])
        self.assertFalse((ROOT / "src/frontend/requirements.txt").exists())
        self.assertFalse((ROOT / "zensical.toml").exists())
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertNotIn("zensical", str(project.get("build-system", {})))
        self.assertNotIn("docs", project.get("dependency-groups", {}))
        lock = tomllib.loads((ROOT / "uv.lock").read_text())
        self.assertFalse(any(p["name"] == "zensical" for p in lock.get("package", [])))

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
        self.assertEqual(publish["with"]["path"], "build/docs")
        ci = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text())
        tasks = [
            item.get("task")
            for job in ci["jobs"].values()
            for item in job.get("strategy", {}).get("matrix", {}).get("include", [])
        ]
        self.assertIn("docs:check", tasks)
        self.assertNotIn("pages", ci["permissions"])

    def test_navigation_scoping_and_search_exclusions(self) -> None:
        """Default sidebar shows User and Self-Hosting; internal docs are search-excluded."""
        config_text = (DOCS_ROOT / ".vitepress/config.ts").read_text(encoding="utf-8")
        default_match = re.search(
            r"const defaultSidebar = \[(.*?)\n\];", config_text, flags=re.DOTALL
        )
        self.assertIsNotNone(default_match, "Missing defaultSidebar in config.ts")
        assert default_match is not None
        default_block = default_match.group(1)
        self.assertIn("User Documentation", default_block)
        self.assertIn("Self-Hosting", default_block)
        for forbidden in (
            "CHECKLIST",
            "PLAN",
            "DESIGN_AGENTIC",
            "AGENT_TROUBLESHOOTING",
            "specs/",
            "ARCHITECTURE_DEEP_DIVE",
            "CONFIGURATION",
        ):
            self.assertNotIn(forbidden, default_block)
        for excluded in (
            "specs/",
            "PLAN.md",
            "CHECKLIST.md",
            "development/DESIGN_AGENTIC.md",
            "development/AGENT_TROUBLESHOOTING.md",
        ):
            self.assertIn(f'"{excluded}"', config_text)
        self.assertIn('"/": defaultSidebar', config_text)
        self.assertIn('"/technical/": technicalSidebar', config_text)
        self.assertIn('"/reference": referenceSidebar', config_text)
        self.assertIn("boost:", config_text)

    def test_active_documentation_editorial_and_link_hygiene(self) -> None:
        """Active guides follow editorial rules and avoid retired/GitHub-blob links."""
        rewritten_pages = [
            ROOT / "README.md",
            DOCS_ROOT / "index.md",
            DOCS_ROOT / "using-camply.md",
            DOCS_ROOT / "cli.md",
            DOCS_ROOT / "technical/index.md",
            DOCS_ROOT / "CONTRIBUTING.md",
            DOCS_ROOT / "reference.md",
            DOCS_ROOT / "PLAN.md",
            *sorted((DOCS_ROOT / "self-hosting").glob("*.md")),
            *sorted((DOCS_ROOT / "development").glob("*.md")),
            *sorted((DOCS_ROOT / "architecture").glob("*.md")),
            *sorted((DOCS_ROOT / "operations").glob("*.md")),
        ]
        self.assert_no_retired_links(rewritten_pages)
        self.assert_no_internal_github_blob_links(rewritten_pages)
        self.assert_editorial_standard(rewritten_pages)

    @unittest.skipUnless(
        (ROOT / "build/docs/index.html").exists(), "Run task docs:build first"
    )
    def test_built_search_index_excludes_internal_artifacts(self) -> None:
        """Built local search index includes user/hosting guides and omits internal docs."""
        chunks = list(
            (ROOT / "build/docs/assets/chunks").glob("@localSearchIndexroot.*.js")
        )
        self.assertTrue(chunks, "Missing VitePress local search index chunk")
        index_text = chunks[0].read_text(encoding="utf-8")
        for included in (
            "/docs/using-camply",
            "/docs/cli",
            "/docs/self-hosting/standalone",
        ):
            self.assertIn(included, index_text)
        for excluded in (
            "/docs/specs/",
            "/docs/PLAN",
            "/docs/CHECKLIST",
            "/docs/development/DESIGN_AGENTIC",
            "/docs/development/AGENT_TROUBLESHOOTING",
        ):
            self.assertNotIn(excluded, index_text)

    @unittest.skipUnless(
        (ROOT / "build/docs/index.html").exists(), "Run task docs:build first"
    )
    def test_rendered_sidebar_scoping(self) -> None:
        """Built pages render only their perspective's scoped sidebar."""
        directory = ROOT / "build/docs"
        expectations = {
            "index.html": ("User Documentation", "Polling Engine"),
            "using-camply.html": ("User Documentation", "Specifications Catalog"),
            "self-hosting/index.html": ("Self-Hosting", "Polling Engine"),
            "technical/index.html": ("Polling Engine", "User Documentation"),
            "CONTRIBUTING.html": ("Polling Engine", "User Documentation"),
            "reference.html": ("Specifications Catalog", "User Documentation"),
            "operations/CONFIGURATION.html": (
                "Specifications Catalog",
                "User Documentation",
            ),
            "PLAN.html": ("Specifications Catalog", "Self-Hosting"),
        }
        for relative, (expected, forbidden) in expectations.items():
            html = (directory / relative).read_text(encoding="utf-8")
            match = re.search(
                r'<aside class="VPSidebar".*?</aside>', html, flags=re.DOTALL
            )
            self.assertIsNotNone(match, f"Missing VPSidebar in {relative}")
            assert match is not None
            sidebar_html = match.group(0)
            with self.subTest(page=relative):
                self.assertIn(expected, sidebar_html)
                self.assertNotIn(forbidden, sidebar_html)

    @unittest.skipUnless(
        (ROOT / "build/docs/index.html").exists(), "Run task docs:build first"
    )
    def test_mermaid_blocks_render_diagram_components(self) -> None:
        """Mermaid code fences render into diagram wrappers instead of raw code blocks."""
        directory = ROOT / "build/docs"
        for relative in (
            "architecture/ARCHITECTURE_DEEP_DIVE.html",
            "operations/RELEASES.html",
        ):
            html = (directory / relative).read_text(encoding="utf-8")
            with self.subTest(page=relative):
                self.assertIn("camply-mermaid", html)
                self.assertNotIn('class="language-mermaid', html)

    @unittest.skipUnless(
        (ROOT / "build/docs/index.html").exists(), "Run task docs:build first"
    )
    def test_rendered_links_and_assets(self) -> None:
        """Every generated page must have working local links and anchors."""
        directory = ROOT / "build/docs"
        pages = {path.resolve(): Page(path) for path in directory.rglob("*.html")}
        source = ROOT / "docs"
        for markdown in source.rglob("*.md"):
            route = markdown.relative_to(source).with_suffix(".html")
            target = directory / route
            self.assertTrue(target.is_file(), f"Missing built page for {markdown}")
        for path, page in pages.items():
            if path.name == "404.html":
                continue
            for link in page.links:
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                with self.subTest(page=path.relative_to(directory), link=link):
                    if url.path.startswith("/docs/"):
                        rel = url.path.removeprefix("/docs/")
                        target = directory / unquote(rel)
                    elif not url.path:
                        target = path
                    else:
                        target = (path.parent / unquote(url.path)).resolve()
                    if target.is_dir():
                        target /= "index.html"
                    self.assertTrue(target.is_file(), f"Missing target: {target}")
                    if url.fragment and target in pages:
                        self.assertIn(unquote(url.fragment), pages[target].anchors)

        self.assert_preserved_routes(directory)

    def assert_preserved_routes(self, build_dir: Path) -> None:
        """Verify required app-linked documentation entrypoints exist in built output."""
        for relative in (
            "index.html",
            "using-camply.html",
            "404.html",
            "assets/camply.svg",
        ):
            self.assertTrue(
                (build_dir / relative).is_file(),
                f"Missing preserved route or asset: {relative}",
            )

    def assert_no_retired_links(self, paths: list[Path]) -> None:
        """Ensure none of the given Markdown files resolve links to retired doc paths."""
        retired_targets = {DOCS_ROOT / name for name in RETIRED_DOCS}
        link_pattern = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for match in link_pattern.finditer(text):
                raw_target = match.group(1)
                if "://" in raw_target or raw_target.startswith("mailto:"):
                    continue
                resolved = (
                    (DOCS_ROOT / raw_target.removeprefix("/docs/")).resolve()
                    if raw_target.startswith("/docs/")
                    else (path.parent / raw_target).resolve()
                )
                with self.subTest(file=path.relative_to(ROOT), link=raw_target):
                    self.assertNotIn(resolved, retired_targets)

    def assert_no_internal_github_blob_links(self, paths: list[Path]) -> None:
        """Ensure site Markdown files link relatively instead of via GitHub blob URLs."""
        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.relative_to(ROOT)):
                self.assertIsNone(
                    _INTERNAL_BLOB_LINK_PATTERN.search(text),
                    f"Use a relative Markdown link instead of GitHub blob URL in {path}",
                )

    def assert_editorial_standard(self, paths: list[Path]) -> None:
        """Verify active rewritten pages follow plain-heading and direct-opener rules."""
        for path in paths:
            lines = path.read_text(encoding="utf-8").splitlines()
            in_fence = False
            first_prose: str | None = None
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if stripped.startswith("#"):
                    with self.subTest(file=path.relative_to(ROOT), heading=stripped):
                        self.assertIsNone(
                            _HEADING_EMOJI_PATTERN.match(stripped),
                            f"Remove decorative emoji from heading in {path}: {stripped}",
                        )
                    continue
                if (
                    first_prose is None
                    and stripped
                    and not stripped.startswith(
                        ("---", "<", "!", "[", "|", ">", "-", "*")
                    )
                ):
                    first_prose = stripped.casefold()
            if first_prose is not None:
                with self.subTest(file=path.relative_to(ROOT), opener=first_prose):
                    self.assertFalse(
                        first_prose.startswith(BANNED_OPENER_PREFIXES),
                        f"Replace filler opener in {path}: {first_prose}",
                    )


if __name__ == "__main__":
    unittest.main()
