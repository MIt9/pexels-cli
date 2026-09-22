"""State builder and compact candidate transformer for decision classifiers (Laya / System 1 models)."""

import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


def extract_slug_from_url(url: str) -> str:
    """Extract human-readable slug from Pexels URL.
    
    Example:
    'https://www.pexels.com/video/a-man-shopping-on-black-friday-5890229/'
    -> 'a man shopping on black friday'
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]
        if not parts:
            return ""
        
        # Take the last meaningful segment (skip 'video', 'photo' if preceding)
        segment = parts[-1]
        
        # Strip trailing numeric ID (e.g. '-5890229' or '5890229')
        slug_part = re.sub(r"-\d+$", "", segment)
        slug_part = re.sub(r"^\d+$", "", slug_part)
        
        # Replace hyphens with spaces
        slug = slug_part.replace("-", " ").strip()
        return slug
    except Exception:
        return ""


def build_candidate_state_item(
    item: Dict[str, Any],
    media_type: str,
    query: Union[str, List[str]],
) -> Dict[str, Any]:
    """Transform raw Pexels photo/video item into a compact, state-ready classifier candidate object.
    
    Output Schema:
    {
      "id": int,
      "type": "video" | "photo",
      "query": str | List[str],
      "photographer": str,
      "state": str,
      "url": str,
      "width": int,
      "height": int,
      "duration": int (videos only)
    }
    """
    url = item.get("url", "")
    slug = extract_slug_from_url(url)
    
    # Photographer / user extraction
    photographer = item.get("photographer", "")
    if not photographer and isinstance(item.get("user"), dict):
        photographer = item.get("user", {}).get("name", "")
    if not photographer:
        photographer = ""
    
    # Tags extraction
    raw_tags = item.get("tags", [])
    tag_list = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, str) and t.strip():
                tag_list.append(t.strip())
            elif isinstance(t, dict) and t.get("name"):
                tag_list.append(str(t.get("name")).strip())

    # Build state string
    state_parts = []
    if slug:
        state_parts.append(slug)
    elif isinstance(query, str) and query:
        state_parts.append(query)
    else:
        state_parts.append(f"Pexels {media_type} #{item.get('id', '')}")

    if tag_list:
        state_parts.append(f"(tags: {', '.join(tag_list)})")

    state_str = " ".join(state_parts)

    candidate = {
        "id": item.get("id"),
        "type": media_type,
        "query": query,
        "photographer": photographer,
        "state": state_str,
        "url": url,
    }

    if media_type == "video" and "duration" in item:
        candidate["duration"] = item.get("duration")

    if "width" in item:
        candidate["width"] = item.get("width")
    if "height" in item:
        candidate["height"] = item.get("height")

    return candidate


VALID_DEDUPE_MODES = ("keep-first", "keep-all-queries")


def deduplicate_candidates(
    candidates: List[Dict[str, Any]],
    mode: str = "keep-first",
) -> List[Dict[str, Any]]:
    """Deduplicate candidate objects by 'id'.
    
    Modes:
    - 'keep-first' / True: keeps first candidate, query remains single string or initial array.
    - 'keep-all-queries': keeps first candidate, but merges query into a list of all matching queries.
    """
    if mode not in VALID_DEDUPE_MODES:
        raise ValueError(f"Invalid dedupe mode '{mode}'. Choices: {', '.join(VALID_DEDUPE_MODES)}")

    seen: Dict[Any, Dict[str, Any]] = {}
    result: List[Dict[str, Any]] = []

    for item in candidates:
        cid = item.get("id")
        if cid is None:
            result.append(item)
            continue

        if cid not in seen:
            item_copy = dict(item)
            if mode == "keep-all-queries":
                q = item_copy.get("query")
                if isinstance(q, str):
                    item_copy["query"] = [q]
                elif not isinstance(q, list):
                    item_copy["query"] = []
            seen[cid] = item_copy
            result.append(item_copy)
        else:
            if mode == "keep-all-queries":
                existing = seen[cid]
                existing_queries = existing.get("query", [])
                if not isinstance(existing_queries, list):
                    existing_queries = [existing_queries]
                new_q = item.get("query")
                if isinstance(new_q, list):
                    for q in new_q:
                        if q not in existing_queries:
                            existing_queries.append(q)
                elif isinstance(new_q, str) and new_q not in existing_queries:
                    existing_queries.append(new_q)
                existing["query"] = existing_queries

    return result


def apply_fields_filter(data: Any, fields: List[str]) -> Any:
    """Filter dictionary/list keys to contain only specified fields.
    Prints a warning to stderr if requested fields are not present in the data.
    """
    if not fields:
        return data

    field_set = set(fields)

    # Collect existing keys to detect non-existent fields
    existing_keys = set()
    has_items = False
    if isinstance(data, dict):
        existing_keys.update(data.keys())
        items = data.get("photos") or data.get("videos")
        if isinstance(items, list) and len(items) > 0:
            has_items = True
            for item in items:
                if isinstance(item, dict):
                    existing_keys.update(item.keys())
    elif isinstance(data, list) and len(data) > 0:
        has_items = True
        for item in data:
            if isinstance(item, dict):
                existing_keys.update(item.keys())

    if existing_keys and (has_items or (isinstance(data, dict) and not ("photos" in data or "videos" in data))):
        missing_fields = [f for f in fields if f not in existing_keys]
        if missing_fields:
            import sys
            from rich.console import Console

            stderr_console = Console(stderr=True)
            missing_str = ", ".join(f"'{f}'" for f in missing_fields)
            stderr_console.print(
                f"[yellow]⚠️ Warning:[/yellow] Field(s) {missing_str} not found in response objects."
            )

    def _filter_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in d.items() if k in field_set}

    if isinstance(data, dict):
        if "photos" in data and isinstance(data["photos"], list):
            res = dict(data)
            res["photos"] = [_filter_dict(p) if isinstance(p, dict) else p for p in data["photos"]]
            return res
        elif "videos" in data and isinstance(data["videos"], list):
            res = dict(data)
            res["videos"] = [_filter_dict(v) if isinstance(v, dict) else v for v in data["videos"]]
            return res
        else:
            return _filter_dict(data)
    elif isinstance(data, list):
        return [_filter_dict(x) if isinstance(x, dict) else x for x in data]

    return data
