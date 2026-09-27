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
                close_session(session.player)

    def on_disable(self):
        for session in list(sessions.values()):
            close_session(session.player)
