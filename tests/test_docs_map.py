"""The agent briefing must list every doc, and the entry points must exist."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
CONTEXT = DOCS / "project-context.md"


def doc_map_targets() -> set[str]:
    text = CONTEXT.read_text(encoding="utf-8")
    section = text.split("## 12. Documentation map", 1)[1]
    return set(re.findall(r"\]\(([\w.-]+\.md)\)", section))


def test_the_documentation_map_lists_every_doc():
    on_disk = {p.name for p in DOCS.glob("*.md")} - {CONTEXT.name}
    listed = doc_map_targets()
    assert on_disk - listed == set(), f"docs missing from the map: {sorted(on_disk - listed)}"


def test_the_documentation_map_lists_no_missing_doc():
    listed = doc_map_targets()
    missing = [name for name in listed if not (DOCS / name).exists()]
    assert missing == [], f"the map links to docs that do not exist: {missing}"


def test_agents_file_points_at_the_briefing_docs():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    for name in ("project-context.md", "vision.md", "decisions.md", "history.md", "progress.md"):
        assert f"docs/{name}" in text, f"AGENTS.md does not mention docs/{name}"


def test_readme_points_agents_to_the_briefing():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    for name in ("AGENTS.md", "docs/project-context.md", "docs/vision.md", "docs/decisions.md", "docs/history.md"):
        assert name in text, f"README.md does not mention {name}"


def test_money_stance_is_recorded_where_agents_will_read_it():
    for path in ("AGENTS.md", "docs/vision.md", "docs/project-context.md"):
        text = (REPO / path).read_text(encoding="utf-8").lower()
        assert "does not like asking for money" in text, f"{path} is missing the money stance"


def test_no_doc_claims_the_owner_reviewed_the_code():
    for path in [REPO / "README.md", REPO / "AGENTS.md", *DOCS.glob("*.md")]:
        text = path.read_text(encoding="utf-8").lower()
        if path.name in ("decisions.md", "progress.md", "history.md"):
            continue  # these describe the correction itself
        assert "and reviewed by the owner" not in text, f"{path.name} overclaims owner review"
