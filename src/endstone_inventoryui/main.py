from endstone.plugin import Plugin
import time

from endstone_inventoryui.listener import EventListener
from endstone_inventoryui.manager.player_manager import sessions, close_session
from endstone_inventoryui.manager import Session


class InventoryUIPlugin(Plugin):
    prefix = "InventoryUI"
    api_version = "0.11"
    load = "POSTWORLD"

    def on_enable(self) -> None:
        self.register_events(EventListener(self))
        self.server.scheduler.run_task(self, self._expire_openings, delay=20, period=20)

    def _expire_openings(self):
        for session in list(sessions.values()):
            if session.state != Session.State.OPEN and time.monotonic() - session.last_progress > 15:
                self.logger.warning(f"InventoryUI opening timed out for {session.player.name}; releasing menu")
                self._close_safely(session)

    def on_disable(self):
        # On shutdown BDS may already have destroyed the retained Player wrappers.
        online = {player.unique_id: player for player in self.server.online_players}
        for player_id, session in list(sessions.items()):
            if player_id in online:
                session.player = online[player_id]
                self._close_safely(session)
            else:
                sessions.pop(player_id, None)
                if session.menu is not None:
                    session.menu._remove_session(session)

    def before_stop(self):
        for session in list(sessions.values()):
            self._close_safely(session)

    def _close_safely(self, session):
        try:
            close_session(session.player)
        except Exception as exc:
            self.logger.error(f"Could not close inventory for {session.player.name}: {exc}")
