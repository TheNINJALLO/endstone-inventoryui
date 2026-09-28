from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from endstone_inventoryui._protocol.packets.packet import NetworkStackLatencyPacket

from endstone_inventoryui.listener import EventListener
from endstone_inventoryui.manager import Session
from endstone_inventoryui.manager.player_manager import sessions, close_session


@pytest.fixture
def session():
    player = SimpleNamespace(unique_id=uuid4(), name="MenuPlayer", send_packet=Mock())
    current = Session(player)
    current._menu = SimpleNamespace(_close_listener=Mock(), _open_listener=Mock(),
                                    _remove_session=Mock(), type=SimpleNamespace(container_type=0))
    sessions[player.unique_id] = current
    player_id = player.unique_id
    yield current
    sessions.pop(player_id, None)


def test_menu_opens_after_matching_ack_without_violation_warning(session):
    listener = EventListener(SimpleNamespace(logger=Mock()))
    session.state = Session.State.OPENING
    session.ack_timestamp = 123_000_000
    session.send_contents = Mock()
    payload = NetworkStackLatencyPacket(123, False).serialize()
    listener._handle_ping(session.player, payload)
    assert session.state == Session.State.OPEN
    session.send_contents.assert_called_once()
    session.menu._open_listener.assert_called_once_with(session.player)
    listener._handle_ping(session.player, payload)
    session.menu._open_listener.assert_called_once()


def test_unrelated_latency_or_warning_cannot_open_menu(session):
    listener = EventListener(SimpleNamespace(logger=Mock()))
    session.state = Session.State.OPENING
    session.ack_timestamp = 123
    listener._handle_ping(session.player, NetworkStackLatencyPacket(456, False).serialize())
    listener._handle_packet_violation_warning(session.player)
    assert session.state == Session.State.OPENING
    session.menu._open_listener.assert_not_called()


def test_disconnect_closes_and_saves_menu_once(session):
    menu = session.menu
    close_session(session.player, send_close=False)
    close_session(session.player, send_close=False)
    assert session.player.unique_id not in sessions
    menu._close_listener.assert_called_once_with(session.player)
    menu._remove_session.assert_called_once_with(session)


def test_failed_close_callback_still_releases_session(session):
    session.menu._close_listener.side_effect = OSError("database unavailable")
    with pytest.raises(OSError):
        close_session(session.player, send_close=False)
    assert session.player.unique_id not in sessions
    session.menu._remove_session.assert_called_once()


def test_close_returns_cursor_overflow_instead_of_deleting_it(session):
    item = object()
    session.player.inventory = SimpleNamespace(add_item=Mock(return_value={0: item}))
    session.player.dimension = SimpleNamespace(drop_item=Mock())
    session.player.location = object()
    session.container_manager = SimpleNamespace(
        cursor_container=SimpleNamespace(get=Mock(return_value=item), set=Mock()),
        sync_player_inventory=Mock(),
    )
    session.close(send_close=False)
    session.player.dimension.drop_item.assert_called_once_with(session.player.location, item)
    session.container_manager.cursor_container.set.assert_called_once_with(0, None)


def test_timeout_releases_unopened_backpack(session, monkeypatch):
    from endstone_inventoryui.main import InventoryUIPlugin
    import endstone_inventoryui.main as module
    session.state = Session.State.GRAPHIC_SENT
    session.last_progress = 1
    monkeypatch.setattr(module.time, "monotonic", lambda: 17)
    plugin = SimpleNamespace(logger=Mock())
    plugin._close_safely = lambda s: InventoryUIPlugin._close_safely(plugin, s)
    InventoryUIPlugin._expire_openings(plugin)
    assert session.player.unique_id not in sessions
    session.menu._close_listener.assert_called_once()


def test_disable_never_dereferences_destroyed_player(session):
    from endstone_inventoryui.main import InventoryUIPlugin
    class DestroyedPlayer:
        def __getattribute__(self, name):
            raise AssertionError("A destroyed native player must not be used")
    session.player = DestroyedPlayer()
    plugin = SimpleNamespace(server=SimpleNamespace(online_players=[]))
    InventoryUIPlugin.on_disable(plugin)
    assert not sessions
    session.menu._remove_session.assert_called_once_with(session)


def test_console_stop_flushes_open_menu_before_native_teardown():
    plugin = SimpleNamespace(before_stop=Mock())
    listener = EventListener(plugin)
    listener.on_server_command(SimpleNamespace(command="stop"))
    plugin.before_stop.assert_called_once()
