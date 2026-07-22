"""P0-A public truth: post-launch copy and public pointers match the live instrument."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, site  # noqa: E402


REPO = Path(__file__).resolve().parent.parent


def test_about_names_and_links_all_three_live_accounts():
    html = site.about_body()
    for handle in ("onscript.news", "blue.onscript.news", "red.onscript.news"):
        assert f'https://bsky.app/profile/{handle}' in html
    assert "post daily" in html
    assert "At public launch" not in html
    assert "have not begun posting" not in html


def test_about_and_methodology_link_the_public_repo_and_release_assets():
    assert config.REPO_URL == "https://github.com/mlawsonking/onscript"
    release_url = f"{config.REPO_URL}/releases/tag/data-latest"
    for html in (site.about_body(), site.methodology_body()):
        assert config.REPO_URL in html
        assert release_url in html


def test_public_copy_calls_the_degraded_voice_a_labeled_deterministic_fallback():
    html = site.about_body()
    assert "deterministic fallback" in html
    assert "plainly labeled" in html
    assert "dry-run</strong> deterministic stub" not in html


def test_empty_post_archive_copy_is_true_in_any_build():
    html = site.posts_log_body([])
    assert "No posts recorded in this build" in html
    assert "have not begun posting" not in html


def test_readme_is_a_post_launch_operator_and_reproduction_runbook():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Launch blockers" not in text
    assert "no remote exists yet" not in text
    for required in ("POSTING_ENABLED", "LLM_VOICE_ENABLED", "pipeline/rebuild.py",
                     "pipeline.redact --check", "data-latest"):
        assert required in text


def test_operations_and_calendar_point_to_the_current_governing_state():
    ops = (REPO / "docs" / "07-OPERATIONS.md").read_text(encoding="utf-8")
    calendar = (REPO / "docs" / "20-DRIP-CALENDAR.md").read_text(encoding="utf-8")
    s2 = next(line for line in ops.splitlines() if "| **S2**" in line)
    s3 = next(line for line in ops.splitlines() if "| **S3**" in line)
    assert "current" not in s2.lower()
    assert "current, 2026-07-22" in s3
    assert "docs/23" in calendar[:1200]
    assert "Session 42" in calendar[:1200]
