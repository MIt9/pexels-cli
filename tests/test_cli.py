import pytest
from typer.testing import CliRunner
from pexels_cli.cli import app, preprocess_args, resolve_query_list
from pexels_cli.client import PexelsClient, PexelsClientError
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


def test_slug_extraction_edge_cases():
    assert extract_slug_from_url("") == ""
    assert extract_slug_from_url("https://www.pexels.com/photo/misty-pine-forest-12345/") == "misty pine forest"
    assert extract_slug_from_url("https://www.pexels.com/video/ocean-waves-67890") == "ocean waves"


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


def test_deduplicate_candidates_invalid_mode():
    cands = [{"id": 1, "query": "q1", "state": "s1"}]
    with pytest.raises(ValueError):
        deduplicate_candidates(cands, mode="invalid")


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


def test_resolve_query_list():
    assert resolve_query_list("mountains", None, None) == ["mountains"]
    assert resolve_query_list(None, "mountains, forest, sunset", None) == ["mountains", "forest", "sunset"]
    with pytest.raises(PexelsClientError):
        resolve_query_list(None, None, None)


def test_resolve_query_list_file(tmp_path):
    q_file = tmp_path / "queries.txt"
    q_file.write_text("mountain lake\n\nforest fog\n")
    resolved = resolve_query_list(None, None, q_file)
    assert resolved == ["mountain lake", "forest fog"]

    non_existent = tmp_path / "missing.txt"
    with pytest.raises(PexelsClientError):
        resolve_query_list(None, None, non_existent)


def test_pexels_client_init_validation():
    with pytest.raises(PexelsClientError):
        PexelsClient(api_key="")


def test_apply_fields_filter_dict_structures():
    photos_payload = {
        "page": 1,
        "per_page": 15,
        "photos": [
            {"id": 100, "url": "http://photo/100", "photographer": "Alice", "width": 1920},
            {"id": 101, "url": "http://photo/101", "photographer": "Bob", "width": 1080},
        ],
    }
    filtered_photos = apply_fields_filter(photos_payload, ["id", "photographer"])
    assert filtered_photos["photos"] == [
        {"id": 100, "photographer": "Alice"},
        {"id": 101, "photographer": "Bob"},
    ]

    videos_payload = {
        "page": 1,
        "videos": [
            {"id": 200, "url": "http://video/200", "duration": 15, "width": 3840},
        ],
    }
    filtered_videos = apply_fields_filter(videos_payload, ["id", "duration"])
    assert filtered_videos["videos"] == [
        {"id": 200, "duration": 15},
    ]



