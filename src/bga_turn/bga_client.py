from __future__ import annotations

import asyncio
import html as html_lib
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import requests
import websockets
from websockets import ConnectionClosed
from websockets.exceptions import InvalidStatus

from .i18n import tr
from .models import BgaNotificationState, BgaTableInfo

LOGGER = logging.getLogger(__name__)


class BgaClientError(RuntimeError):
    pass


class BgaNotPublicError(BgaClientError):
    pass


class BgaTableUnavailableError(BgaNotPublicError):
    pass


@dataclass(frozen=True)
class SpectatorBootstrap:
    user_id: str
    username: str
    credentials: str
    websocket_url: str | None = None


class BgaClient:
    _HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
    _CURRENT_PLAYER_NAME_PATTERN = re.compile(
        r'globalThis\.gameui\.current_player_name\s*=\s*"(?P<username>[^"]+)"'
    )
    _COMPLETE_SETUP_PATTERN = re.compile(
        r'globalThis\.gameui\.completesetup\(\s*"(?P<game_name>[^"]+)"\s*,\s*"(?P<game_label>[^"]+)"\s*,\s*(?P<table_id>\d+)\s*,\s*(?P<user_id>-?\d+)\s*,\s*(?:/\*archivemask_begin\*/)?"(?P<credentials>[0-9a-fA-F]{32,64})"',
        re.DOTALL,
    )
    _PLAYERS_OBJECT_START_PATTERN = re.compile(r'"players"\s*:\s*\{', re.IGNORECASE)
    _PLAYER_ARRAY_START_PATTERN = re.compile(r'"player"\s*:\s*\[', re.IGNORECASE)
    _PLAYER_ENTRY_PATTERNS = [
        re.compile(
            r'"player_id"\s*:\s*"?(?P<player_id>\d+)"?.{0,2000}?"player_name"\s*:\s*"(?P<player_name>[^"]+)"',
            re.DOTALL,
        ),
        re.compile(
            r'"player_name"\s*:\s*"(?P<player_name>[^"]+)".{0,2000}?"player_id"\s*:\s*"?(?P<player_id>\d+)"?',
            re.DOTALL,
        ),
        re.compile(
            r'"id"\s*:\s*"?(?P<player_id>\d+)"?.{0,4000}?"fullname"\s*:\s*"(?P<player_name>[^"]+)"',
            re.DOTALL | re.IGNORECASE,
        ),
        re.compile(
            r'"fullname"\s*:\s*"(?P<player_name>[^"]+)".{0,4000}?"id"\s*:\s*"?(?P<player_id>\d+)"?',
            re.DOTALL | re.IGNORECASE,
        ),
        re.compile(
            r'"player_id"\s*:\s*"?(?P<player_id>\d+)"?.{0,2000}?"fullname"\s*:\s*"(?P<player_name>[^"]+)"',
            re.DOTALL | re.IGNORECASE,
        ),
        re.compile(
            r'"fullname"\s*:\s*"(?P<player_name>[^"]+)".{0,2000}?"player_id"\s*:\s*"?(?P<player_id>\d+)"?',
            re.DOTALL | re.IGNORECASE,
        ),
        re.compile(
            r'"playerId"\s*:\s*"?(?P<player_id>\d+)"?.{0,2000}?"(?:playerName|name|fullname|username)"\s*:\s*"(?P<player_name>[^"]+)"',
            re.DOTALL | re.IGNORECASE,
        ),
        re.compile(
            r'"(?:playerName|name|fullname|username)"\s*:\s*"(?P<player_name>[^"]+)".{0,2000}?"playerId"\s*:\s*"?(?P<player_id>\d+)"?',
            re.DOTALL | re.IGNORECASE,
        ),
        re.compile(
            r'"(?P<player_id>\d+)"\s*:\s*\{(?=[^}]{0,4000}"(?:avatar|rank|table_status|color|zombie|score|table_order|country|played|is_admin|is_premium|no|eliminated|scoreAux|crystal)"[^}]{0,4000}).{0,4000}?"(?:name|fullname|player_name|username)"\s*:\s*"(?P<player_name>[^"]+)"',
            re.DOTALL | re.IGNORECASE,
        ),
    ]
    _PLAYER_ID_KEYS = ("player_id", "playerid", "player", "id", "user", "user_id", "userid")
    _PLAYER_NAME_KEYS = ("player_name", "playername", "name", "fullname", "full_name", "username")
    _PLAYERISH_KEYS = {
        "avatar",
        "rank",
        "color",
        "score",
        "table_status",
        "is_admin",
        "is_premium",
        "table_order",
        "country",
        "zombie",
        "gamerank",
        "finish_game",
        "played",
    }
    _GAMESTATE_PATTERN = re.compile(
        r'"gamestate":\{"id":(?P<state_id>\d+).*?"active_player":"(?P<active_player>\d+)"',
        re.DOTALL,
    )
    _GAMESTATES_BLOCK_PATTERN = re.compile(
        r'"gamestates":\{(?P<body>.*?)\},"notifications"',
        re.DOTALL,
    )
    _MULTIACTIVE_PATTERN = re.compile(
        r'"multiactive"\s*:\s*\[(?P<ids>[^\]]*)\]',
        re.DOTALL,
    )
    _CENTRIFUGE_WS_PATTERN = re.compile(
        r'"transport"\s*:\s*"websocket"\s*,\s*"endpoint"\s*:\s*"(?P<url>wss[^"]+)"',
        re.DOTALL,
    )
    _LEGACY_BOOTSTRAP_PATTERNS = [
        re.compile(
            r'"user_id"\s*:\s*"(?P<user_id>-?\d+)".{0,500}?"username"\s*:\s*"(?P<username>[^"]+)".{0,500}?"credentials"\s*:\s*"(?P<credentials>[0-9a-fA-F]{16,})"',
            re.DOTALL,
        ),
        re.compile(
            r'user_id\s*:\s*"(?P<user_id>-?\d+)".{0,500}?username\s*:\s*"(?P<username>[^"]+)".{0,500}?credentials\s*:\s*"(?P<credentials>[0-9a-fA-F]{16,})"',
            re.DOTALL,
        ),
    ]

    def __init__(
        self,
        timeout: int = 30,
        websocket_url: str = "wss://ws-x1.boardgamearena.com/connection/websocket",
        *,
        enable_tableinfos_fallback: bool = False,
    ) -> None:
        self.timeout = timeout
        self.websocket_url = websocket_url
        self.enable_tableinfos_fallback = enable_tableinfos_fallback
        self._http = requests.Session()
        self._http.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en,en-US;q=0.9,fr;q=0.8,fr-FR;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

    def build_public_table_info(
        self,
        *,
        table_id: str,
        table_url: str,
        base_url: str,
        gameserver: str,
        game_name: str,
    ) -> BgaTableInfo:
        return BgaTableInfo(
            table_id=table_id,
            table_url=table_url,
            base_url=base_url,
            gameserver=gameserver,
            game_name=game_name,
        )

    def fetch_public_table_finished_status(self, table_info: BgaTableInfo) -> bool | None:
        data = self._fetch_public_tableinfos_data(
            table_id=table_info.table_id,
            base_url=table_info.base_url,
        )
        status_value = str(data.get("status") or "").strip().lower()
        result = data.get("result")
        result_dict = result if isinstance(result, dict) else {}
        endgame_reason = str(result_dict.get("endgame_reason") or "").strip()
        time_end = str(result_dict.get("time_end") or "").strip()
        cancelled = str(data.get("cancelled") or "").strip()

        is_finished = (
            status_value == "finished"
            or bool(endgame_reason)
            or bool(time_end)
            or cancelled == "1"
        )
        LOGGER.info(
            tr(
                "tableinfos_status",
                table_id=table_info.table_id,
                status=status_value or "n/a",
                cancelled=cancelled or "n/a",
                time_end=time_end or "n/a",
                endgame_reason=endgame_reason or "n/a",
                finished=is_finished,
            )
        )
        return is_finished

    def fetch_public_player_names(self, table_info: BgaTableInfo) -> dict[str, str]:
        try:
            response = self._http.get(table_info.table_url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise BgaClientError(
                tr("error_load_public_page", table_url=table_info.table_url, error=exc)
            ) from exc

        if response.status_code >= 400:
            raise BgaClientError(tr("error_public_page_http", status_code=response.status_code))

        return self._extract_player_names_from_html(response.text)

    def _fetch_public_tableinfos_data(self, *, table_id: str, base_url: str) -> dict[str, Any]:
        endpoint = (
            f"{base_url}/table/table/tableinfos.html"
            f"?id={table_id}&nosuggest=true&table={table_id}"
            f"&noerrortracking=true&dojo.preventCache={int(time.time() * 1000)}"
        )
        try:
            response = self._http.get(endpoint, timeout=self.timeout)
        except requests.RequestException as exc:
            raise BgaClientError(tr("error_load_tableinfos", table_id=table_id, error=exc)) from exc

        if response.status_code >= 400:
            raise BgaClientError(
                tr("error_tableinfos_http", status_code=response.status_code, table_id=table_id)
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise BgaClientError(tr("error_tableinfos_invalid_json", table_id=table_id)) from exc

        if not isinstance(payload, dict):
            raise BgaClientError(tr("error_tableinfos_unexpected", table_id=table_id))

        if str(payload.get("status")) != "1":
            raise BgaClientError(
                tr(
                    "error_tableinfos_unexpected_payload",
                    table_id=table_id,
                    status=str(payload.get("status") or "n/a"),
                    exception=str(payload.get("exception") or "n/a"),
                    error=str(payload.get("error") or "n/a"),
                )
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            raise BgaClientError(tr("error_tableinfos_missing_data", table_id=table_id))
        return data

    async def probe_public_table(
        self,
        table_info: BgaTableInfo,
        known_player_names: dict[str, str] | None = None,
    ) -> BgaNotificationState:
        known_names = dict(known_player_names or {})
        bootstrap, bootstrap_state = await asyncio.to_thread(self._load_public_bootstrap, table_info)
        pending_items: list[dict[str, Any]] = []

        async with self._connect(table_info, websocket_url=bootstrap.websocket_url) as websocket:
            await self._connect_and_subscribe(websocket, table_info, bootstrap, pending_items)
            presence_state = await self._request_presence(websocket, table_info, known_names, pending_items)
            if presence_state is not None:
                known_names.update(presence_state.player_names)

            if bootstrap_state is not None:
                merged_names = dict(bootstrap_state.player_names)
                merged_names.update(known_names)
                bootstrap_state = BgaNotificationState(
                    highest_packet_id=bootstrap_state.highest_packet_id,
                    waiting_ids=bootstrap_state.waiting_ids,
                    player_names=merged_names,
                    source=bootstrap_state.source,
                    details=bootstrap_state.details,
                )

            initial_states = self._extract_states_from_items(
                items=pending_items,
                current_waiting_ids=[],
                known_player_names=known_names,
            )
            if initial_states:
                return initial_states[-1]
            if bootstrap_state is not None:
                return bootstrap_state
            if presence_state is not None:
                return presence_state

            try:
                message = await asyncio.wait_for(self._recv_message(websocket), timeout=3)
            except asyncio.TimeoutError:
                return BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=None,
                    player_names=known_names,
                    source="websocket_subscribed",
                    details={"probe": "subscribed_without_immediate_publication"},
                    is_game_finished=False,
                )

            states = self._extract_states_from_frame(
                message=message,
                current_waiting_ids=[],
                known_player_names=known_names,
            )
            if states:
                return states[-1]
            return BgaNotificationState(
                highest_packet_id=None,
                waiting_ids=None,
                player_names=known_names,
                source="websocket_subscribed",
                details={"probe": "no_state_in_first_publication"},
                is_game_finished=False,
            )

    async def watch_table(
        self,
        table_info: BgaTableInfo,
        current_waiting_ids: list[str],
        known_player_names: dict[str, str],
    ):
        bootstrap, bootstrap_state = await asyncio.to_thread(self._load_public_bootstrap, table_info)
        pending_items: list[dict[str, Any]] = []

        async with self._connect(table_info, websocket_url=bootstrap.websocket_url) as websocket:
            await self._connect_and_subscribe(websocket, table_info, bootstrap, pending_items)
            presence_state = await self._request_presence(websocket, table_info, known_player_names, pending_items)
            if presence_state is not None:
                known_player_names = dict(presence_state.player_names)
                yield presence_state

            if bootstrap_state is not None:
                merged_names = dict(bootstrap_state.player_names)
                merged_names.update(known_player_names)
                bootstrap_state = BgaNotificationState(
                    highest_packet_id=bootstrap_state.highest_packet_id,
                    waiting_ids=bootstrap_state.waiting_ids,
                    player_names=merged_names,
                    source=bootstrap_state.source,
                    details=bootstrap_state.details,
                )
                if bootstrap_state.player_names:
                    known_player_names = dict(bootstrap_state.player_names)
                    yield bootstrap_state
                if bootstrap_state.waiting_ids is not None and bootstrap_state.waiting_ids != current_waiting_ids:
                    current_waiting_ids = list(bootstrap_state.waiting_ids)
                    known_player_names = dict(bootstrap_state.player_names)

            initial_states = self._extract_states_from_items(
                items=pending_items,
                current_waiting_ids=current_waiting_ids,
                known_player_names=known_player_names,
            )
            for state in initial_states:
                if state.waiting_ids is not None:
                    current_waiting_ids = state.waiting_ids
                known_player_names = dict(state.player_names)
                yield state

            while True:
                try:
                    message = await asyncio.wait_for(self._recv_message(websocket), timeout=30)
                except asyncio.TimeoutError:
                    if not self.enable_tableinfos_fallback:
                        continue
                    try:
                        finished_publicly = await asyncio.to_thread(
                            self.fetch_public_table_finished_status,
                            table_info,
                        )
                    except BgaClientError as exc:
                        LOGGER.warning(
                            tr(
                                "idle_tableinfos_check_failed",
                                table_id=table_info.table_id,
                                error=exc,
                            )
                        )
                        continue
                    if finished_publicly:
                        yield BgaNotificationState(
                            highest_packet_id=None,
                            waiting_ids=[],
                            player_names=dict(known_player_names),
                            source="table_finished_poll",
                            details={"probe": "idle_tableinfos_status"},
                            is_game_finished=True,
                    )
                        return
                    continue
                except ConnectionClosed as exc:
                    raise BgaClientError(tr("error_websocket_closed", error=exc)) from exc

                states = self._extract_states_from_frame(
                    message=message,
                    current_waiting_ids=current_waiting_ids,
                    known_player_names=known_player_names,
                )
                for state in states:
                    if state.waiting_ids is not None:
                        current_waiting_ids = state.waiting_ids
                    known_player_names = dict(state.player_names)
                    yield state

    def _load_public_bootstrap(self, table_info: BgaTableInfo) -> tuple[SpectatorBootstrap, BgaNotificationState | None]:
        try:
            response = self._http.get(table_info.table_url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise BgaClientError(
                tr("error_load_public_page", table_url=table_info.table_url, error=exc)
            ) from exc

        if response.status_code >= 400:
            raise BgaNotPublicError(tr("error_public_page_http", status_code=response.status_code))

        if table_info.gameserver and table_info.game_name:
            expected_path_segment = f"/{table_info.gameserver}/{table_info.game_name}"
            if expected_path_segment not in response.url:
                raise BgaTableUnavailableError(
                    tr("error_table_redirected_to_lobby", final_url=response.url)
                )

        html = response.text
        bootstrap = self._extract_spectator_bootstrap(html)
        if bootstrap is None:
            raise BgaNotPublicError(tr("error_missing_spectator_bootstrap"))
        initial_state = self._extract_initial_state_from_html(html)
        return bootstrap, initial_state

    @classmethod
    def _extract_spectator_bootstrap(cls, html: str) -> SpectatorBootstrap | None:
        websocket_url = cls._extract_websocket_url(html)
        current_name_match = cls._CURRENT_PLAYER_NAME_PATTERN.search(html)
        setup_match = cls._COMPLETE_SETUP_PATTERN.search(html)
        if current_name_match and setup_match:
            return SpectatorBootstrap(
                user_id=setup_match.group("user_id").strip(),
                username=current_name_match.group("username").strip(),
                credentials=setup_match.group("credentials").strip(),
                websocket_url=websocket_url,
            )

        candidates = [html, html.replace('\\"', '"')]
        for candidate in candidates:
            for pattern in cls._LEGACY_BOOTSTRAP_PATTERNS:
                match = pattern.search(candidate)
                if not match:
                    continue
                user_id = match.group("user_id").strip()
                username = match.group("username").strip()
                credentials = match.group("credentials").strip()
                if not user_id or not username or not credentials:
                    continue
                return SpectatorBootstrap(
                    user_id=user_id,
                    username=username,
                    credentials=credentials,
                    websocket_url=websocket_url,
                )
        return None

    @classmethod
    def _extract_websocket_url(cls, html: str) -> str | None:
        match = cls._CENTRIFUGE_WS_PATTERN.search(html)
        if match is None:
            return None
        return match.group("url").replace("\\/", "/")

    @classmethod
    def _extract_initial_state_from_html(cls, html: str) -> BgaNotificationState | None:
        player_names = cls._extract_player_names_from_html(html)
        gamestate_match = cls._GAMESTATE_PATTERN.search(html)
        if not gamestate_match:
            if player_names:
                return BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=None,
                    player_names=player_names,
                    source="page_bootstrap_players",
                    details={"bootstrap": "players_only"},
                    is_game_finished=False,
                )
            return None

        state_id = gamestate_match.group("state_id").strip()
        active_player = gamestate_match.group("active_player").strip()
        if not active_player.isdigit():
            if player_names:
                return BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=None,
                    player_names=player_names,
                    source="page_bootstrap_players",
                    details={"bootstrap": "players_only", "state_id": state_id},
                    is_game_finished=False,
                )
            return None

        state_type = cls._extract_gamestate_type(html, state_id)
        if state_type == "multipleactiveplayer":
            multiactive_ids = cls._extract_multiactive_player_ids(html)
            if multiactive_ids:
                return BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=multiactive_ids,
                    player_names=player_names,
                    source="page_bootstrap_multiactive",
                    details={"state_id": state_id, "state_type": state_type},
                    is_game_finished=False,
                )
        if state_type is None or state_type == "multipleactiveplayer":
            if player_names:
                details: dict[str, str] = {"bootstrap": "players_only", "state_id": state_id}
                if state_type is not None:
                    details["state_type"] = state_type
                return BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=None,
                    player_names=player_names,
                    source="page_bootstrap_players",
                    details=details,
                    is_game_finished=False,
                )
            return None
        if state_type not in {"activeplayer", "private", "manager"}:
            if player_names:
                return BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=None,
                    player_names=player_names,
                    source="page_bootstrap_players",
                    details={
                        "bootstrap": "players_only",
                        "state_id": state_id,
                        "state_type": state_type,
                    },
                    is_game_finished=False,
                )
            return None

        return BgaNotificationState(
            highest_packet_id=None,
            waiting_ids=[active_player],
            player_names=player_names,
            source="page_bootstrap_active_player",
            details={"state_id": state_id, "state_type": state_type},
            is_game_finished=False,
        )

    @classmethod
    def _extract_multiactive_player_ids(cls, html: str) -> list[str]:
        match = cls._MULTIACTIVE_PATTERN.search(html)
        if match is None:
            return []
        return re.findall(r"\d+", match.group("ids"))

    @classmethod
    def _extract_gamestate_type(cls, html: str, state_id: str) -> str | None:
        gamestates_match = cls._GAMESTATES_BLOCK_PATTERN.search(html)
        if gamestates_match is None:
            return None
        gamestates_body = gamestates_match.group("body")
        pattern = re.compile(
            rf'"{re.escape(state_id)}":\{{.*?"type":"(?P<state_type>[^"]+)"',
            re.DOTALL,
        )
        match = pattern.search(gamestates_body)
        if match is None:
            return None
        return match.group("state_type").strip()

    @classmethod
    def _extract_player_names_from_html(cls, html: str) -> dict[str, str]:
        player_names: dict[str, str] = {}
        for block in cls._iter_player_candidate_blocks(html):
            parsed_block = cls._try_parse_json_fragment(block)
            if parsed_block is not None:
                cls._collect_player_names(player_names, parsed_block)
            for pattern in cls._PLAYER_ENTRY_PATTERNS:
                for match in pattern.finditer(block):
                    cls._remember_player_name(
                        player_names,
                        match.group("player_id"),
                        match.group("player_name"),
                    )
        return player_names

    @classmethod
    def _iter_player_candidate_blocks(cls, html: str):
        seen: set[str] = set()
        for candidate in (html, html.replace('\\"', '"')):
            for pattern in (cls._PLAYERS_OBJECT_START_PATTERN, cls._PLAYER_ARRAY_START_PATTERN):
                for match in pattern.finditer(candidate):
                    start_index = match.end() - 1
                    block = cls._extract_balanced_segment(candidate, start_index)
                    if not block or block in seen:
                        continue
                    seen.add(block)
                    yield block

    @classmethod
    def _extract_balanced_segment(cls, text: str, start_index: int) -> str | None:
        if start_index < 0 or start_index >= len(text):
            return None
        opening_char = text[start_index]
        closing_char = "}" if opening_char == "{" else "]" if opening_char == "[" else ""
        if not closing_char:
            return None

        depth = 0
        in_string = False
        escaped = False
        for index in range(start_index, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == opening_char:
                depth += 1
                continue
            if char == closing_char:
                depth -= 1
                if depth == 0:
                    return text[start_index : index + 1]
        return None

    @staticmethod
    def _try_parse_json_fragment(fragment: str) -> Any | None:
        try:
            return json.loads(fragment)
        except ValueError:
            return None

    async def _connect_and_subscribe(
        self,
        websocket: Any,
        table_info: BgaTableInfo,
        bootstrap: SpectatorBootstrap,
        pending_items: list[dict[str, Any]],
    ) -> None:
        await self._send_command_and_wait(
            websocket,
            1,
            {
                "id": 1,
                "connect": {
                    "data": {
                        "user_id": bootstrap.user_id,
                        "username": bootstrap.username,
                        "credentials": bootstrap.credentials,
                    },
                    "name": "js",
                },
            },
            expected_reply_keys=("connect",),
            pending_items=pending_items,
        )

        channels = [
            (2, "bgamsg"),
            (3, "/general/emergency"),
            (4, f"/player/p{bootstrap.user_id}"),
            (5, f"/table/t{table_info.table_id}"),
        ]
        for command_id, channel in channels:
            await self._send_command_and_wait(
                websocket,
                command_id,
                {
                    "id": command_id,
                    "subscribe": {
                        "channel": channel,
                    },
                },
                expected_reply_keys=("subscribe",),
                pending_items=pending_items,
            )

    async def _request_presence(
        self,
        websocket: Any,
        table_info: BgaTableInfo,
        known_player_names: dict[str, str],
        pending_items: list[dict[str, Any]],
    ) -> BgaNotificationState | None:
        try:
            presence_reply = await self._send_command_and_wait(
                websocket,
                6,
                {
                    "id": 6,
                    "presence": {
                        "channel": f"/table/t{table_info.table_id}",
                    },
                },
                expected_reply_keys=("presence",),
                pending_items=pending_items,
                timeout=5,
            )
        except BgaClientError:
            return None

        presence_payload = presence_reply.get("presence")
        if not isinstance(presence_payload, dict):
            return None
        presence_items = presence_payload.get("presence")
        if not isinstance(presence_items, dict):
            return None

        player_names = dict(known_player_names)
        for info in presence_items.values():
            if not isinstance(info, dict):
                continue
            player_id = self._coerce_player_id(info.get("user"))
            if not player_id:
                continue
            conn_info = info.get("conn_info")
            if not isinstance(conn_info, dict):
                continue
            self._remember_player_name(player_names, player_id, conn_info.get("username"))

        return BgaNotificationState(
            highest_packet_id=None,
            waiting_ids=None,
            player_names=player_names,
            source="presence",
            details={"probe": "presence_snapshot"},
            is_game_finished=False,
        )

    async def _send_command_and_wait(
        self,
        websocket: Any,
        command_id: int,
        command: dict[str, Any],
        *,
        expected_reply_keys: tuple[str, ...],
        pending_items: list[dict[str, Any]],
        timeout: int | None = None,
    ) -> dict[str, Any]:
        await websocket.send(json.dumps(command) + "\n")
        deadline = timeout or self.timeout
        while True:
            try:
                raw_message = await asyncio.wait_for(self._recv_message(websocket), timeout=deadline)
            except asyncio.TimeoutError as exc:
                raise BgaClientError(tr("error_websocket_command_timeout", command_id=command_id)) from exc
            except ConnectionClosed as exc:
                raise BgaClientError(
                    tr("error_websocket_command_closed", command_id=command_id, error=exc)
                ) from exc

            for item in self._decode_frame(raw_message):
                if item.get("id") == command_id:
                    if item.get("error"):
                        raise BgaClientError(str(item["error"]))
                    for key in expected_reply_keys:
                        if key in item:
                            return item
                    if "result" in item:
                        return item
                else:
                    pending_items.append(item)

    async def _recv_message(self, websocket: Any) -> str:
        while True:
            raw_message = await websocket.recv()
            items = self._decode_frame(raw_message)
            if any(not item for item in items):
                await websocket.send("{}\n")
                items = [item for item in items if item]
                if not items:
                    continue
                return "\n".join(json.dumps(item) for item in items)
            return raw_message

    @asynccontextmanager
    async def _connect(self, table_info: BgaTableInfo, websocket_url: str | None = None):
        effective_url = websocket_url or self.websocket_url
        try:
            async with websockets.connect(
                effective_url,
                origin=table_info.base_url,
                user_agent_header=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
                open_timeout=self.timeout,
                ping_interval=None,
                ping_timeout=None,
            ) as websocket:
                yield websocket
        except InvalidStatus as exc:
            raise BgaClientError(
                tr(
                    "error_websocket_handshake_rejected",
                    table_id=table_info.table_id,
                    status_code=exc.response.status_code,
                )
            ) from exc
        except TimeoutError as exc:
            raise BgaClientError(
                tr(
                    "error_websocket_handshake_timeout",
                    table_id=table_info.table_id,
                    websocket_url=effective_url,
                )
            ) from exc

    def _extract_states_from_frame(
        self,
        *,
        message: str,
        current_waiting_ids: list[str],
        known_player_names: dict[str, str],
    ) -> list[BgaNotificationState]:
        return self._extract_states_from_items(
            items=self._decode_frame(message),
            current_waiting_ids=current_waiting_ids,
            known_player_names=known_player_names,
        )

    def _extract_states_from_items(
        self,
        *,
        items: list[dict[str, Any]],
        current_waiting_ids: list[str],
        known_player_names: dict[str, str],
    ) -> list[BgaNotificationState]:
        states: list[BgaNotificationState] = []
        local_waiting_ids = list(current_waiting_ids)
        local_player_names = dict(known_player_names)
        for item in items:
            states_from_item = self._extract_states_from_item(
                item=item,
                current_waiting_ids=local_waiting_ids,
                known_player_names=local_player_names,
            )
            for state in states_from_item:
                states.append(state)
                if state.waiting_ids is not None:
                    local_waiting_ids = state.waiting_ids
                local_player_names = dict(state.player_names)
        return states

    def _extract_states_from_item(
        self,
        *,
        item: dict[str, Any],
        current_waiting_ids: list[str],
        known_player_names: dict[str, str],
    ) -> list[BgaNotificationState]:
        push = item.get("push")
        if not isinstance(push, dict):
            return []

        states: list[BgaNotificationState] = []
        local_waiting_ids = list(current_waiting_ids)
        local_player_names = dict(known_player_names)
        self._collect_player_names(local_player_names, push)
        if local_player_names != known_player_names:
            states.append(
                BgaNotificationState(
                    highest_packet_id=None,
                    waiting_ids=None,
                    player_names=dict(local_player_names),
                    source="player_names_update",
                    details={"probe": "push_only"},
                    is_game_finished=False,
                )
            )

        pub = push.get("pub")
        if isinstance(pub, dict):
            packet = pub.get("data")
            if isinstance(packet, dict):
                packet_states = self._extract_states_from_packet(
                    packet=packet,
                    current_waiting_ids=local_waiting_ids,
                    known_player_names=local_player_names,
                )
                for state in packet_states:
                    states.append(state)
                    if state.waiting_ids is not None:
                        local_waiting_ids = state.waiting_ids
                    local_player_names = dict(state.player_names)
        return states

    def _extract_states_from_packet(
        self,
        *,
        packet: dict[str, Any],
        current_waiting_ids: list[str],
        known_player_names: dict[str, str],
    ) -> list[BgaNotificationState]:
        packet_id = self._coerce_int(packet.get("packet_id"))
        events = packet.get("data")
        if not isinstance(events, list):
            return []

        player_names = dict(known_player_names)
        self._collect_player_names(player_names, packet)
        waiting_ids = list(current_waiting_ids)
        source: str | None = None
        details: dict[str, str] = {}

        for event in events:
            if not isinstance(event, dict):
                continue

            event_type = str(event.get("type") or "")
            event_args = event.get("args")
            self._collect_player_names(player_names, event)

            if event_type == "gameStateMultipleActiveUpdate" and isinstance(event_args, list):
                waiting_ids = [str(player_id) for player_id in event_args if str(player_id).isdigit()]
                source = "multiple_active_update"
                details = {}
                continue

            if event_type == "yourturnack" and isinstance(event_args, dict):
                if len(current_waiting_ids) > 1:
                    continue
                player_id = self._coerce_player_id(event_args.get("player"))
                if player_id:
                    waiting_ids = [player_id]
                    source = "yourturnack"
                    details = {}
                continue

            if event_type == "gameStateChange" and isinstance(event_args, dict):
                active_player = self._coerce_player_id(event_args.get("active_player"))
                state_type = str(event_args.get("type") or "")
                if state_type and state_type != "multipleactiveplayer" and active_player:
                    waiting_ids = [active_player]
                    source = "game_state_change"
                    details = {}
                continue

            if event_type in {"beginTurn", "takeAnAction"}:
                participant_ids = sorted(set(player_names.keys()) | set(waiting_ids))
                if participant_ids:
                    waiting_ids = participant_ids
                    source = "public_turn_window"
                    details = {"heuristic": "begin_turn_or_take_action"}
                continue

            if event_type == "recapTurnActionForOtherPlayers" and isinstance(event_args, dict):
                player_id = self._coerce_player_id(event_args.get("player_id"))
                if player_id and player_id in waiting_ids:
                    waiting_ids = [item for item in waiting_ids if item != player_id]
                    source = "public_turn_window"
                    details = {"heuristic": "recap_action_removal"}
                continue

            if event_type == "endPrivateAction":
                waiting_ids = []
                source = "public_turn_window"
                details = {"heuristic": "end_private_action"}
                continue

            if event_type == "tableInfosChanged" and isinstance(event_args, dict):
                status_value = str(event_args.get("status") or "").strip().lower()
                reload_reason = str(event_args.get("reload_reason") or "").strip()
                result_payload = event_args.get("result")
                result_dict = result_payload if isinstance(result_payload, dict) else {}
                endgame_reason = str(result_dict.get("endgame_reason") or "").strip()
                time_end = str(result_dict.get("time_end") or "").strip()
                if (
                    status_value == "finished"
                    or reload_reason == "tableDestroy"
                    or bool(endgame_reason)
                    or bool(time_end)
                ):
                    waiting_ids = []
                    source = "game_finished"
                    details = {
                        "event_type": event_type,
                        "reload_reason": reload_reason or "n/a",
                        "status": status_value or "n/a",
                    }
                    return [
                        BgaNotificationState(
                            highest_packet_id=packet_id,
                            waiting_ids=waiting_ids,
                            player_names=player_names,
                            source=source,
                            details=details,
                            is_game_finished=True,
                        )
                    ]

            event_log = str(event.get("log") or "").strip().lower()
            if event_type.lower() in {"simplenode", "simplenote"} and "end of game" in event_log:
                waiting_ids = []
                source = "game_finished"
                details = {"event_type": event_type}
                return [
                    BgaNotificationState(
                        highest_packet_id=packet_id,
                        waiting_ids=waiting_ids,
                        player_names=player_names,
                        source=source,
                        details=details,
                        is_game_finished=True,
                    )
                ]

        if source is None:
            if player_names != known_player_names:
                return [
                    BgaNotificationState(
                        highest_packet_id=packet_id,
                        waiting_ids=None,
                        player_names=player_names,
                        source="player_names_update",
                        details={"probe": "packet_names_only"},
                        is_game_finished=False,
                    )
                ]
            return []

        return [
            BgaNotificationState(
                highest_packet_id=packet_id,
                waiting_ids=waiting_ids,
                player_names=player_names,
                source=source,
                details=details,
                is_game_finished=False,
            )
        ]

    @staticmethod
    def _decode_frame(message: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for line in message.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.debug(tr("invalid_json_frame", line=line))
                continue
            if isinstance(value, dict):
                items.append(value)
        return items

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_player_id(value: Any) -> str | None:
        if value is None:
            return None
        candidate = str(value).strip()
        if not candidate.isdigit():
            return None
        return candidate

    @classmethod
    def _clean_player_name(cls, value: Any) -> str:
        raw_value = str(value or "").strip()
        if not raw_value:
            return ""
        unescaped = html_lib.unescape(raw_value)
        without_tags = cls._HTML_TAG_PATTERN.sub("", unescaped)
        normalized = re.sub(r"\s+", " ", without_tags).strip()
        if not normalized or normalized.startswith("Visitor-"):
            return ""
        return normalized

    @classmethod
    def _remember_player_name(cls, player_names: dict[str, str], player_id: Any, player_name: Any) -> None:
        normalized_player_id = cls._coerce_player_id(player_id)
        normalized_player_name = cls._clean_player_name(player_name)
        if normalized_player_id and normalized_player_name:
            player_names[normalized_player_id] = normalized_player_name

    @classmethod
    def _extract_direct_name(cls, payload: dict[str, Any]) -> str:
        normalized_items = {str(key).strip().casefold(): value for key, value in payload.items()}
        for key in cls._PLAYER_NAME_KEYS:
            candidate = cls._clean_player_name(normalized_items.get(key))
            if candidate:
                return candidate
        return ""

    @classmethod
    def _looks_like_player_mapping(cls, payload: dict[str, Any]) -> bool:
        normalized_keys = {str(key).strip().casefold() for key in payload}
        if normalized_keys.intersection(cls._PLAYER_ID_KEYS):
            return True
        if normalized_keys.intersection(cls._PLAYERISH_KEYS):
            return True
        return False

    @classmethod
    def _collect_player_names(cls, player_names: dict[str, str], event_args: Any) -> None:
        if isinstance(event_args, dict):
            normalized_items = {str(key).strip().casefold(): value for key, value in event_args.items()}
            candidate_ids = {
                candidate_id
                for key in cls._PLAYER_ID_KEYS
                if (candidate_id := cls._coerce_player_id(normalized_items.get(key))) is not None
            }
            candidate_name = cls._extract_direct_name(event_args)
            if candidate_name:
                for candidate_id in candidate_ids:
                    cls._remember_player_name(player_names, candidate_id, candidate_name)

            for raw_key, raw_value in event_args.items():
                if not isinstance(raw_value, dict):
                    continue
                key_player_id = cls._coerce_player_id(raw_key)
                if key_player_id is None or not cls._looks_like_player_mapping(raw_value):
                    continue
                nested_name = cls._extract_direct_name(raw_value)
                if nested_name:
                    cls._remember_player_name(player_names, key_player_id, nested_name)

            for raw_value in event_args.values():
                cls._collect_player_names(player_names, raw_value)
            return
        if isinstance(event_args, list):
            for item in event_args:
                cls._collect_player_names(player_names, item)
