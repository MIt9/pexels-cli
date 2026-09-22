"""Tests for Pexels CLI."""

from typer.testing import CliRunner
from pexels_cli.cli import app, preprocess_args
from pexels_cli.config import load_config
from pexels_cli.state_builder import (
    apply_fields_filter,
    build_candidate_state_item,
    deduplicate_candidates,
    extract_slug_from_url,
)

runner = CliRunner()


def test_preprocess_args():
    assert preprocess_args(["px", "videos", "--state", "--dedupe"]) == ["px", "videos", "--state", "--dedupe=keep-first"]
    assert preprocess_args(["px", "videos", "--state", "--dedupe", "keep-all-queries"]) == ["px", "videos", "--state", "--dedupe", "keep-all-queries"]
    assert preprocess_args(["px", "videos", "--state", "--dedupe=keep-all-queries"]) == ["px", "videos", "--state", "--dedupe=keep-all-queries"]
    assert preprocess_args(["px", "videos", "--state", "--dedupe", "--per-page", "5"]) == ["px", "videos", "--state", "--dedupe=keep-first", "--per-page", "5"]


def test_slug_extraction():
    url = "https://www.pexels.com/video/a-man-shopping-on-black-friday-5890229/"
    assert extract_slug_from_url(url) == "a man shopping on black friday"


def test_build_candidate_state_item():
    item = {
        "id": 5890229,
        "url": "https://www.pexels.com/video/a-man-shopping-on-black-friday-5890229/",
        "user": {"name": "Pavel Danilyuk"},
        "tags": [],
        "duration": 10,
        "width": 2160,
        "height": 3840,
    }
    cand = build_candidate_state_item(item, media_type="video", query="black friday shopping")
    assert cand["id"] == 5890229
    assert cand["type"] == "video"
    assert cand["query"] == "black friday shopping"
    assert cand["photographer"] == "Pavel Danilyuk"
    assert cand["state"] == "a man shopping on black friday"
    assert cand["duration"] == 10
    assert cand["width"] == 2160
    assert cand["height"] == 3840

    item_with_tags = {
        "id": 5890229,
        "url": "https://www.pexels.com/video/a-man-shopping-on-black-friday-5890229/",
        "photographer": "Pavel Danilyuk",
        "tags": ["retail", "sale"],
    }
    cand_tags = build_candidate_state_item(item_with_tags, media_type="video", query="black friday shopping")
    assert cand_tags["photographer"] == "Pavel Danilyuk"
    assert cand_tags["state"] == "a man shopping on black friday (tags: retail, sale)"


def test_deduplicate_candidates():
    cands = [
        {"id": 1, "query": "q1", "state": "s1"},
        {"id": 1, "query": "q2", "state": "s1"},
        {"id": 2, "query": "q2", "state": "s2"},
    ]
    deduped_first = deduplicate_candidates(cands, mode="keep-first")
    assert len(deduped_first) == 2
    assert deduped_first[0]["query"] == "q1"

    deduped_all = deduplicate_candidates(cands, mode="keep-all-queries")
    assert len(deduped_all) == 2
    assert deduped_all[0]["query"] == ["q1", "q2"]


def test_version_command():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "pexels-cli version 0.2.4" in result.output

    res_cmd = runner.invoke(app, ["version"])
    assert res_cmd.exit_code == 0
    assert "pexels-cli v0.2.4" in res_cmd.output

    res_json = runner.invoke(app, ["version", "--json"])
    assert res_json.exit_code == 0
    assert '"version": "0.2.4"' in res_json.output


def test_sanitize_response():
    from pexels_cli.client import _sanitize_response

    payload = {
        "page": 1,
        "next_page": "https://api.pexels.com/v1/v1/search?page=2&per_page=15",
        "prev_page": "https://api.pexels.com/v1/v1/search?page=1&per_page=15",
        "nested": {
            "next_page": "https://api.pexels.com/v1/v1/v1/photos"
        }
    }
    sanitized = _sanitize_response(payload)
    assert sanitized["next_page"] == "https://api.pexels.com/v1/search?page=2&per_page=15"
    assert sanitized["prev_page"] == "https://api.pexels.com/v1/search?page=1&per_page=15"
    assert sanitized["nested"]["next_page"] == "https://api.pexels.com/v1/photos"


def test_invalid_dedupe_validation():
    result = runner.invoke(app, ["search", "mountains", "--dedupe", "invalid-mode"])
    assert result.exit_code != 0
    assert "Invalid dedupe mode 'invalid-mode'" in result.output


def test_fields_filter_warning(capsys):
    data = [{"id": 1, "url": "https://pexels.com/1"}]
    filtered = apply_fields_filter(data, ["id", "non_existent_field"])
    assert filtered == [{"id": 1}]
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "non_existent_field" in captured.err


