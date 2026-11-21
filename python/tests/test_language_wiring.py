"""Tests that each language with data is wired into the demo and site, and the agents are listed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from jayasree.languages import LANGUAGES, data_paths

ROOT = Path(__file__).resolve().parent.parent.parent
WITH_DATA = {
    name: spec for name, spec in LANGUAGES.items() if data_paths(spec).stroke_data.exists()
}
AGENTS = {p.stem: p for p in sorted((ROOT / ".claude" / "agents").glob("*.md"))}
#: Reviews code diffs; not a stage of the onboarding pipeline.
NOT_PIPELINE = {"code-reviewer"}


def _wordmark(code: str) -> str:
    """Return the repo-relative wordmark path (Malayalam's is unsuffixed)."""
    return "demo/jayasree.svg" if code == "ml" else f"demo/jayasree.{code}.svg"


@pytest.mark.parametrize("name", sorted(WITH_DATA))
def test_language_has_a_demo_tab(name: str) -> None:
    """Ensure that a language with processed strokes has an entry in the demo's LANGUAGES table."""
    code = WITH_DATA[name].code
    demo_js = (ROOT / "demo" / "demo.js").read_text(encoding="utf-8")
    assert f'code: "{code}"' in demo_js


@pytest.mark.parametrize("name", sorted(WITH_DATA))
def test_language_has_a_wordmark_shown_on_the_readme_and_site(name: str) -> None:
    """Ensure that a language's wordmark exists and both the README and the home page show it."""
    path = _wordmark(WITH_DATA[name].code)
    assert (ROOT / path).is_file(), f"{path} is missing: tools/export_wordmark.py --lang {name}"
    for page in ("README.md", "index.html"):
        shown = f'<img src="{path}"' in (ROOT / page).read_text(encoding="utf-8")
        assert shown, f"{page} does not show {path}"


@pytest.mark.parametrize("name", sorted(WITH_DATA))
def test_readme_names_the_language(name: str) -> None:
    """Ensure that the README mentions each language that has data."""
    assert WITH_DATA[name].name in (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("agent", sorted(AGENTS))
def test_agent_file_name_matches_its_frontmatter(agent: str) -> None:
    """Ensure that each agent file's frontmatter name is the file name."""
    head = AGENTS[agent].read_text(encoding="utf-8").split("---")[1]
    assert re.search(rf"^name: {re.escape(agent)}$", head, re.MULTILINE)


@pytest.mark.parametrize("agent", sorted(set(AGENTS) - NOT_PIPELINE))
def test_pipeline_agent_is_in_the_spec_and_the_skill(agent: str) -> None:
    """Ensure that every pipeline agent appears in the onboarding spec and in /onboard-language."""
    spec = (ROOT / "docs" / "LANGUAGE_ONBOARDING_AGENTS.md").read_text(encoding="utf-8")
    skill = (ROOT / ".claude" / "skills" / "onboard-language" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert f"`{agent}`" in spec, f"{agent} is not in docs/LANGUAGE_ONBOARDING_AGENTS.md"
    assert f"`{agent}`" in skill, f"{agent} is not in the onboard-language skill"
