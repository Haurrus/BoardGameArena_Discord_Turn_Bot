from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import requests
import websockets
from websockets import ConnectionClosed

from models import BgaNotificationState, BgaTableInfo

LOGGER = logging.getLogger(__name__)


class BgaClientError(RuntimeError):
    pass


class BgaNotPublicError(BgaClientError):
    pass


@dataclass(frozen=True)
class SpectatorBootstrap:
    user_id: str
    username: str
    credentials: str


class BgaClient:
    _CURRENT_PLAYER_NAME_PATTERN = re.compile(
        r'globalThis\.gameui\.current_player_name\s*=\s*"(?P<username>[^"]+)"'
    )
    _COMPLETE_SETUP_PATTERN = re.compile(
        r'globalThis\.gameui\.completesetup\(\s*"(?P<game_name>[^"]+)"\s*,\s*"(?P<game_label>[^"]+)"\s*,\s*(?P<table_id>\d+)\s*,\s*(?P<user_id>-?\d+)\s*,\s*(?:/\*archivemask_begin\*/)?"(?P<credentials>[0-9a-fA-F]{32,64})"',
        re.DOTALL,
    )
    _PLAYER_ENTRY_PATTERN = re.compile(
        r'"(?P<player_id>\d+)":\{"id":"(?P=player_id)".{0,200}?"name":"(?P<player_name>[^"]+)"',
        re.DOTALL,
    )
    _GAMESTATE_PATTERN = re.compile(
        r'"gamestate":\{"id":(?P<state_id>\d+).*?"active_player":"(?P<active_player>\d+)"',
        re.DOTALL,
    )
    _GAMESTATES_BLOCK_PATTERN = re.compile(
        r'"gamestates":\{(?P<body>.*?)\},"notifications"',
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

    def __init__(self, timeout: int = 30, websocket_url: str = "wss://ws-x1.boardgamearena.com/connection/websocket") -> None:
        self.timeout = timeout
        self.websocket_url = websocket_url
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

    async def probe_public_table(
        self,
        table_info: BgaTableInfo,
        known_player_names: dict[str, str] | None = None,
    ) -> BgaNotificationState:
        known_names = dict(known_player_names or {})
        bootstrap, bootstrap_state = await asyncio.to_thread(self._load_public_bootstrap, table_info)
        pending_items: list[dict[str, Any]] = []

        async with self._connect(table_info) as websocket:
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
            )

    async def watch_table(
        self,
        table_info: BgaTableInfo,
        current_waiting_ids: list[str],
        known_player_names: dict[str, str],
    ):
        bootstrap, bootstrap_state = await asyncio.to_thread(self._load_public_bootstrap, table_info)
        pending_items: list[dict[str, Any]] = []

        async with self._connect(table_info) as websocket:
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
                    message = await self._recv_message(websocket)
                except ConnectionClosed as exc:
                    raise BgaClientError(f"Connexion websocket fermee: {exc}") from exc

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
            raise BgaClientError(f"Impossible de charger la page publique {table_info.table_url}: {exc}") from exc

        if response.status_code >= 400:
            raise BgaNotPublicError(f"La page publique renvoie HTTP {response.status_code}.")

        html = response.text
        bootstrap = self._extract_spectator_bootstrap(html)
        if bootstrap is None:
            raise BgaNotPublicError(
                "Impossible d'extraire l'identite spectateur anonyme depuis la page publique."
            )
        initial_state = self._extract_initial_state_from_html(html)
        return bootstrap, initial_state

    @classmethod
    def _extract_spectator_bootstrap(cls, html: str) -> SpectatorBootstrap | None:
        current_name_match = cls._CURRENT_PLAYER_NAME_PATTERN.search(html)
        setup_match = cls._COMPLETE_SETUP_PATTERN.search(html)
        if current_name_match and setup_match:
            return SpectatorBootstrap(
                user_id=setup_match.group("user_id").strip(),
                username=current_name_match.group("username").strip(),
                credentials=setup_match.group("credentials").strip(),
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
                )
        return None

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
                )
            return None

        state_type = cls._extract_gamestate_type(html, state_id)
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
                )
            return None

        return BgaNotificationState(
            highest_packet_id=None,
            waiting_ids=[active_player],
            player_names=player_names,
            source="page_bootstrap_active_player",
            details={"state_id": state_id, "state_type": state_type},
        )

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
        for match in cls._PLAYER_ENTRY_PATTERN.finditer(html):
            player_id = match.group("player_id").strip()
            player_name = match.group("player_name").strip()
            if player_id and player_name:
                player_names[player_id] = player_name
        return player_names

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
            username = str(conn_info.get("username") or "").strip()
            if username:
                player_names[player_id] = username

        return BgaNotificationState(
            highest_packet_id=None,
            waiting_ids=None,
            player_names=player_names,
            source="presence",
            details={"probe": "presence_snapshot"},
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
                raise BgaClientError(f"Timeout sur la commande websocket {command_id}.") from exc
            except ConnectionClosed as exc:
                raise BgaClientError(f"Connexion websocket fermee pendant la commande {command_id}: {exc}") from exc

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

    def _connect(self, table_info: BgaTableInfo):
        return websockets.connect(
            self.websocket_url,
            origin=table_info.base_url,
            user_agent_header=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            open_timeout=self.timeout,
            ping_interval=None,
            ping_timeout=None,
        )

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
        waiting_ids = list(current_waiting_ids)
        source: str | None = None
        details: dict[str, str] = {}

        for event in events:
            if not isinstance(event, dict):
                continue

            event_type = str(event.get("type") or "")
            event_args = event.get("args")
            self._collect_player_names(player_names, event_args)

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

        if source is None:
            return []

        return [
            BgaNotificationState(
                highest_packet_id=packet_id,
                waiting_ids=waiting_ids,
                player_names=player_names,
                source=source,
                details=details,
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
                LOGGER.debug("Trame websocket BGA ignoree car JSON invalide: %s", line)
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
    def _collect_player_names(cls, player_names: dict[str, str], event_args: Any) -> None:
        if not isinstance(event_args, dict):
            return

        player_id = cls._coerce_player_id(event_args.get("player_id"))
        player_name = str(event_args.get("player_name") or "").strip()
        if player_id and player_name:
            player_names[player_id] = player_name

        draft_rows = event_args.get("draftCrossedBuildings")
        if isinstance(draft_rows, list):
            for row in draft_rows:
                if not isinstance(row, dict):
                    continue
                nested_id = cls._coerce_player_id(row.get("player_id"))
                nested_name = str(row.get("player_name") or "").strip()
                if nested_id and nested_name:
                    player_names[nested_id] = nested_name
