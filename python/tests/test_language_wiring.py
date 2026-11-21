"""Tests that languages are wired into the demo and site, and the agent files are consistent."""

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


def _frontmatter(agent: str) -> dict[str, str]:
    """Return an agent file's frontmatter as a flat dict of its `key: value` lines."""
    head = AGENTS[agent].read_text(encoding="utf-8").split("---")[1]
    return dict(re.findall(r"^(\w+): (.*)$", head, re.MULTILINE))


def _tools(agent: str) -> set[str]:
    """Return the tool names an agent is granted."""
    return {t.strip() for t in _frontmatter(agent)["tools"].split(",")}


@pytest.mark.parametrize("agent", sorted(AGENTS))
def test_agent_declares_description_tools_and_model(agent: str) -> None:
    """Ensure that each agent file has a description, a tools list and a model."""
    fields = _frontmatter(agent)
    assert {"description", "tools", "model"} <= fields.keys()
    assert fields["description"].strip("\"'") != ""


@pytest.mark.parametrize("agent", sorted(set(AGENTS) - NOT_PIPELINE))
def test_pipeline_agent_only_runs_when_asked(agent: str) -> None:
    """Ensure that a pipeline agent's description says it is used only when explicitly asked."""
    assert "explicitly asked" in _frontmatter(agent)["description"]


def test_reviewing_agent_cannot_write() -> None:
    """Ensure that the read-only profile reviewer has no Write or Edit tool."""
    assert not _tools("language-reviewer") & {"Write", "Edit"}


@pytest.mark.parametrize("agent", ["atom-reducer", "language-publisher"])
def test_agent_that_edits_existing_files_can_edit(agent: str) -> None:
    """Ensure that agents which modify existing files (registry, demo, README) hold Edit."""
    assert "Edit" in _tools(agent)


def test_spec_has_the_sections_the_adapters_point_at() -> None:
    """Ensure that every spec heading an adapter or the skill relies on exists."""
    spec = (ROOT / "docs" / "LANGUAGE_ONBOARDING_AGENTS.md").read_text(encoding="utf-8")
    for heading in (
        "### Agent 1",
        "### Agent 2",
        "### Agent 3",
        "### Stage 7 - wire up and document",
        "### Stage 8 - freeze",
        "### Post-recording gate (stage 5)",
        "## Don't generalize from Malayalam",
    ):
        assert re.search(rf"^{re.escape(heading)}", spec, re.MULTILINE), heading


def test_skill_names_every_stage_it_acts_on() -> None:
    """Ensure that the skill mentions each stage in which an agent or command does the work."""
    skill = (ROOT / ".claude" / "skills" / "onboard-language" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for stage in (1, 2, 3, 4, 5, 7, 8):
        assert f"Stage {stage}" in skill or f"**Stage {stage}**" in skill, f"Stage {stage}"


def test_make_targets_named_in_the_pipeline_docs_exist() -> None:
    """Ensure that every `make <target>` the spec, skill and adapters name is in the Makefile."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-z][\w-]*):", makefile, re.MULTILINE))
    texts = [
        ROOT / "docs" / "LANGUAGE_ONBOARDING_AGENTS.md",
        ROOT / ".claude" / "skills" / "onboard-language" / "SKILL.md",
        *AGENTS.values(),
    ]
    named = {t for f in texts for t in re.findall(r"`make ([a-z][\w-]*)", f.read_text("utf-8"))}
    assert named <= targets, f"not in the Makefile: {sorted(named - targets)}"
