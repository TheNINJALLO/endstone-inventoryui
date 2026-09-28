from endstone_inventoryui._protocol.packets import MinecraftPacketIds
from endstone_inventoryui._protocol.packets.enums import ItemStackRequestActionType
from endstone_inventoryui._protocol.packets.packet import (
    ContainerClosePacket,
    ItemRegistryPacket,
    NetworkStackLatencyPacket,
)
from endstone.event import event_handler, EventPriority, PlayerQuitEvent, PacketReceiveEvent, PacketSendEvent, ServerCommandEvent, PlayerCommandEvent
from endstone.inventory import ItemStack
from endstone.plugin import Plugin

from .manager import Session
from .manager.container.item_stack_response_builder import ItemStackResponseBuilder
from .manager.player_manager import find_session, close_session
from .menu.menu_transaction import MenuTransaction
from .network.container_ui_ids import ContainerUIIds
from .network.item_stack_request_packet import (
    ItemStackRequestPacket,
    UnsupportedItemStackRequestAction,
)
from .network.item_stack_response_packet import ItemStackResponse, ItemStackResponsePacket
from .util.item_utils import all_item_data, add_item_data


class EventListener:
    def __init__(self, plugin: Plugin):
        self._plugin = plugin

    @staticmethod
    def _is_virtual_slot(slot_info) -> bool:
        return slot_info.container.container_enum == ContainerUIIds.LEVEL_ENTITY

    @classmethod
    def _get_virtual_slot(cls, source, destination) -> int:
        if cls._is_virtual_slot(source):
            return source.slot
        if cls._is_virtual_slot(destination):
            return destination.slot
        return -1

    def _create_menu_transaction(self, player, menu, session, action, source, destination) -> MenuTransaction | None:
        slot = self._get_virtual_slot(source, destination)
        if slot == -1:
            return None

        item_clicked = menu.inventory.get_item(slot)
        clicked_with_slot_info = destination if self._is_virtual_slot(source) else source
        clicked_with_container, clicked_with_slot = session.container_manager.get_container_adapter_and_slot(
            clicked_with_slot_info,
        )
        item_clicked_with = clicked_with_container.get(clicked_with_slot) or ItemStack("minecraft:air")

        return MenuTransaction(
            player=player,
            slot=slot,
            item_clicked=item_clicked,
            item_clicked_with=item_clicked_with,
            action_type=action.action_type,
            source=source,
            destination=destination,
            amount=action.action_data.amount,
        )

    @staticmethod
    def _handle_menu_transaction(menu, transaction: MenuTransaction | None) -> bool:
        if transaction is None:
            return True
        if menu._listener is None:
            return False
        result = menu._listener(transaction)
        return result is not None and result.should_continue

    @staticmethod
    def _send_item_stack_responses(player, responses: list[ItemStackResponse]) -> None:
        if not responses:
            return
        pk = ItemStackResponsePacket(responses)
        player.send_packet(pk.get_packet_id(), pk.serialize())

    def _reject_item_stack_request(
        self,
        player,
        session,
        responses: list[ItemStackResponse],
        client_request_id: int,
    ) -> None:
        session.container_manager.discard_transaction()
        responses.append(ItemStackResponseBuilder.build_error(client_request_id))

    def _apply_menu_action(
        self,
        player,
        session,
        menu,
        action,
        source,
        destination,
        responses: list[ItemStackResponse],
        client_request_id: int,
    ) -> bool:
        transaction = self._create_menu_transaction(player, menu, session, action, source, destination)
        if not self._handle_menu_transaction(menu, transaction):
            return False
        if self._is_virtual_slot(source) and self._is_virtual_slot(destination) and source.slot != destination.slot:
            other = self._create_menu_transaction(player, menu, session, action, destination, source)
            if not self._handle_menu_transaction(menu, other):
                return False
        return True

    def _handle_item_stack_request(self, player, session, menu, pk: ItemStackRequestPacket) -> None:
        responses: list[ItemStackResponse] = []
        for req_data in pk.request.request_data:
            session.container_manager.begin_request(req_data.client_request_id)
            try:
                for action in req_data.request_actions:
                    match action.action_type:
                        case ItemStackRequestActionType.Drop:
                            source = action.action_data.source
                            if self._is_virtual_slot(source):
                                if not self._apply_menu_action(
                                        player, session, menu, action, source, source,
                                        responses, req_data.client_request_id,
                                ):
                                    raise ValueError("Menu rejected drop")
                            session.container_manager.handle_drop(
                                source,
                                action.action_data.amount,
                            )
                        case ItemStackRequestActionType.Swap:
                            source = action.action_data.source
                            destination = action.action_data.distination
                            if not self._apply_menu_action(
                                player, session, menu, action, source, destination,
                                responses, req_data.client_request_id,
                            ):
                                raise ValueError("Menu rejected swap")
                            session.container_manager.handle_swap(source, destination)
                        case ItemStackRequestActionType.Take | ItemStackRequestActionType.Place:
                            source = action.action_data.source
                            destination = action.action_data.distination
                            if not self._apply_menu_action(
                                player, session, menu, action, source, destination,
                                responses, req_data.client_request_id,
                            ):
                                raise ValueError("Menu rejected transfer")
                            session.container_manager.transfer_items(
                                source, destination, action.action_data.amount,
                            )
                        case _:
                            raise ValueError(f"Unsupported item stack request action: {action.action_type}")

                responses.append(session.container_manager.commit_transaction())
            except Exception as error:
                self._plugin.logger.debug(f"Error handling item stack request: {error}")
                self._reject_item_stack_request(player, session, responses, req_data.client_request_id)

        self._send_item_stack_responses(player, responses)

    def _handle_ping(self, player, payload: bytes) -> None:
        session = find_session(player)
        if session is None:
            return

        pk = NetworkStackLatencyPacket()
        pk.deserialize(payload)
        if not self._timestamps_match(session.ack_timestamp, pk.timestamp):
            return

        match session.state:
            case Session.State.GRAPHIC_SENT:
                session.update_state(Session.State.GRAPHIC_RECEIVED)
            case Session.State.GRAPHIC_DATA_SENT:
                session.update_state(Session.State.GRAPHIC_DATA_RECEIVED)
            case Session.State.OPENING:
                # This reply follows ContainerOpen in the ordered stream.
                # Current clients need not emit PacketViolationWarning.
                session.update_state(Session.State.OPEN)
                if session.menu._open_listener is not None:
                    session.menu._open_listener(player)

    @staticmethod
    def _timestamps_match(expected: int, received: int) -> bool:
        """Match the raw or scaled latency timestamp without fuzzy accepts."""
        if expected <= 0 or received <= 0:
            return False
        if expected == received:
            return True
        return any(
            expected == received * scale or received == expected * scale
            for scale in (1_000, 1_000_000)
        )

    def _handle_container_close(self, player, payload: bytes) -> None:
        session = find_session(player)
        if session is None:
            return

        pk = ContainerClosePacket()
        pk.deserialize(payload)
        if pk.container_id != Session.CONTAINER_ID:
            return

        if session.pending:
            if session.state != Session.State.CLOSING:
                session.close(send_close=False)
            session.menu = session.pending.popleft()
            session.send_menu()
        else:
            close_session(player, send_close=False)

    def _handle_packet_violation_warning(self, player) -> None:
        session = find_session(player)
        if session is None or session.state != Session.State.OPENING:
            return

        # A warning is not proof that the client opened this menu. Only the
        # matching latency acknowledgement may advance the opening state.
        self._plugin.logger.debug("Client reported a packet violation while opening InventoryUI")

    def _handle_item_stack_request_packet(self, player, payload: bytes) -> bool:
        session = find_session(player)
        if session is None or session.state != Session.State.OPEN:
            return False

        pk = ItemStackRequestPacket()
        try:
            pk.deserialize(payload)
        except UnsupportedItemStackRequestAction as error:
            self._plugin.logger.debug(str(error))
            responses = []
            self._reject_item_stack_request(
                player,
                session,
                responses,
                error.request_id,
            )
            self._send_item_stack_responses(player, responses)
            return True
        except Exception as error:
            # Never pass a partially decoded virtual-container request into
            # BDS. Close the fake container cleanly instead of risking a bad
            # packet disconnect or corrupting the player's inventory state.
            self._plugin.logger.warning(
                f"Closing InventoryUI session after invalid item stack request: {error}"
            )
            session.close(sync_inventory=True)
            close_session(player)
            return True
        self._handle_item_stack_request(player, session, session.menu, pk)
        return True

    @event_handler(priority=EventPriority.NORMAL)
    def on_packet_receive(self, event: PacketReceiveEvent):
        player = event.player
        if player is None:
            return

        match event.packet_id:
            case MinecraftPacketIds.Ping:
                self._handle_ping(player, event.payload)
            case MinecraftPacketIds.ContainerClose:
                self._handle_container_close(player, event.payload)
            case MinecraftPacketIds.PacketViolationWarning:
                self._handle_packet_violation_warning(player)
            case MinecraftPacketIds.ItemStackRequest:
                if self._handle_item_stack_request_packet(player, event.payload):
                    event.cancel()

    @event_handler
    def on_packet_send(self, event: PacketSendEvent):
        if event.packet_id == MinecraftPacketIds.ItemRegistryPacket and len(all_item_data()) == 0:
            pk = ItemRegistryPacket()
            pk.deserialize(event.payload)
            for item in pk.item_registry:
                add_item_data(item.item_name, item)

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent):
        close_session(event.player)

    @event_handler(priority=EventPriority.MONITOR, ignore_cancelled=True)
    def on_server_command(self, event: ServerCommandEvent):
        command = event.command.strip().lstrip("/").split()
        if command and command[0].lower().split(":")[-1] == "stop":
            self._plugin.before_stop()

    @event_handler(priority=EventPriority.MONITOR, ignore_cancelled=True)
    def on_player_command(self, event: PlayerCommandEvent):
        command = event.command.strip().lstrip("/").split()
        if command and command[0].lower().split(":")[-1] == "stop" and event.player.is_op:
            self._plugin.before_stop()
