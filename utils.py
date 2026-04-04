from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from i18n import tr

BASE_URL = "https://boardgamearena.com"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_table_id(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError(tr("error_empty_table_value"))
    if candidate.isdigit():
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        table_values = parse_qs(parsed.query).get("table")
        if table_values and table_values[0].isdigit():
            return table_values[0]

    match = re.search(r"table=(\d+)", candidate)
    if match:
        return match.group(1)

    raise ValueError(tr("error_invalid_table_id"))


def parse_public_table_url(value: str) -> tuple[str, str, str, str, str]:
    candidate = value.strip()
    if not candidate:
        raise ValueError(tr("error_empty_table_url"))

    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(tr("error_watch_requires_full_public_url"))

    table_values = parse_qs(parsed.query).get("table")
    if not table_values or not table_values[0].isdigit():
        raise ValueError(tr("error_url_missing_table_param"))
    table_id = table_values[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        raise ValueError(tr("error_url_missing_public_path"))

    gameserver = path_parts[-2].strip()
    game_name = path_parts[-1].strip()
    if not gameserver or not game_name:
        raise ValueError(tr("error_url_missing_game_path"))

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    normalized_url = f"{base_url}/{gameserver}/{game_name}?table={table_id}"
    return table_id, normalized_url, base_url, gameserver, game_name


def build_table_url(table_id: str) -> str:
    return f"{BASE_URL}/table?table={table_id}"


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


def json_loads_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def json_loads_dict(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        key_str = str(key)
        item_str = str(item).strip()
        if key_str and item_str:
            result[key_str] = item_str
    return result


def format_game_name(game_name: str | None) -> str:
    if not game_name:
        return tr("value_unknown").capitalize()
    return re.sub(r"[_-]+", " ", game_name).strip().title()
