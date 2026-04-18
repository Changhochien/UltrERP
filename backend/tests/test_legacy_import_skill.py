from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / ".agents" / "skills" / "legacy-import"
SKILL_FILE = SKILL_DIR / "SKILL.md"
COMMAND_MAP_FILE = SKILL_DIR / "command-map.md"
SAFETY_GUIDE_FILE = SKILL_DIR / "safety-and-validation.md"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_legacy_import_skill_frontmatter_and_links() -> None:
    skill_text = _read(SKILL_FILE)

    assert SKILL_FILE.exists()
    assert COMMAND_MAP_FILE.exists()
    assert SAFETY_GUIDE_FILE.exists()
    assert skill_text.startswith("---\n")
    assert "\nname: legacy-import\n" in skill_text
    assert "description: Guide the reviewed UltrERP legacy-import workflow" in skill_text
    assert "allowed-tools" not in skill_text
    assert "[the command map](./command-map.md)" in skill_text
    assert "[the safety and validation guide](./safety-and-validation.md)" in skill_text



def test_legacy_import_skill_documents_machine_readable_validation() -> None:
    command_map_text = _read(COMMAND_MAP_FILE)
    safety_guide_text = _read(SAFETY_GUIDE_FILE)

    assert "uv run python -m domains.legacy_import.cli validate-import" in command_map_text
    assert "json=" in safety_guide_text
    assert "markdown=" in safety_guide_text
    assert "blocking_issue_count" in safety_guide_text
    assert "replay.scope_key" in safety_guide_text
    assert "no canonical import run exists" in safety_guide_text


def test_legacy_import_skill_documents_live_stage_and_env_requirements() -> None:
    skill_text = _read(SKILL_FILE)
    command_map_text = _read(COMMAND_MAP_FILE)
    safety_guide_text = _read(SAFETY_GUIDE_FILE)
    env_example_text = _read(ENV_EXAMPLE_FILE)

    assert "live-stage" in skill_text
    assert "uv run python -m domains.legacy_import.cli live-stage" in command_map_text
    assert "`live-stage`" in safety_guide_text
    assert "LEGACY_DB_HOST" in env_example_text
    assert "LEGACY_DB_PASSWORD" in env_example_text
    assert "legacy-import live-stage" in env_example_text
