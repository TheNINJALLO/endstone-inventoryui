from collections import deque
from enum import Enum
from typing import TYPE_CHECKING
import time

from endstone_inventoryui._protocol.packets.packet import ContainerClosePacket
from endstone_inventoryui._protocol.packets.types import BlockPos
from endstone import Player

from endstone_inventoryui.manager.container.container_manager import ContainerManager
from endstone_inventoryui.menu.graphic.block_graphic import BlockGraphic
from endstone_inventoryui.menu.graphic.block_pair_graphic import BlockPairGraphic
from endstone_inventoryui.menu.graphic.graphic import Graphic

if TYPE_CHECKING:
    from endstone_inventoryui.menu import Menu
from endstone_inventoryui.network.inventory_content_packet import InventoryContentPacket
from endstone_inventoryui.network.inventory_slot_packet import InventorySlotPacket
from endstone_inventoryui.network.item_stack_wrapper import ItemStackWrapper
from endstone_inventoryui.util.utils import send_ack_packet, get_block_behind


class Session:
    CONTAINER_ID: int = 2

    MAX_OPEN_ATTEMPTS: int = 10

    class State(Enum):
        NONE = 0
        GRAPHIC_SENT = 1
        GRAPHIC_RECEIVED = 2
        GRAPHIC_DATA_SENT = 3
        GRAPHIC_DATA_RECEIVED = 4
        OPENING = 5
        OPEN = 6
        CLOSING = 7

    def __init__(self, player: Player):
        self.player: Player = player
        self._menu: 'Menu | None' = None
        self.state: Session.State = self.State.NONE
        self.graphic: Graphic | None = None
        self.container_manager: ContainerManager | None = None
        self.block_pos: list[BlockPos] = []
        self.open_attempts = 0
        self.ack_timestamp = 0
        self.pending: deque['Menu'] = deque()
        self.last_progress = time.monotonic()
        self._closed = False

    @property
    def menu(self) -> 'Menu | None':
        return self._menu

    @menu.setter
    def menu(self, value: 'Menu | None') -> None:
        if self._menu is not None:
            self._menu._remove_session(self)
        self._menu = value
        if value is not None:
            value._add_session(self)
            self.container_manager: ContainerManager = ContainerManager(self.player, value.inventory)

    def send_menu(self):
        self._closed = False
        self.last_progress = time.monotonic()
        self.open_attempts = 0
        self.ack_timestamp = 0
        pos = get_block_behind(self.player, 2)
        self.graphic = BlockPairGraphic(self.menu, pos) if self.menu.type.is_pair else BlockGraphic(self.menu, pos)
        self.send_graphic()

    def send_graphic(self):
        self.graphic.send(self.player)
        self.state = self.State.GRAPHIC_SENT
        self.ack_timestamp = send_ack_packet(self.player)

    def send_graphic_data(self):
        self.graphic.send_data(self.player)
        self.state = self.State.GRAPHIC_DATA_SENT
        self.ack_timestamp = send_ack_packet(self.player)

    def open(self):
        self.state = self.State.OPENING
        self.graphic.open(self.player)
        self.ack_timestamp = send_ack_packet(self.player)

    def send_contents(self):
        inventory = self.menu.inventory
        pk = InventoryContentPacket(Session.CONTAINER_ID)
        for i in range(inventory.size):
            item_stack = inventory.get_item(i)
            stack_id = self.container_manager.assign_virtual_slot(i, item_stack)
            pk.items.append(ItemStackWrapper(stack_id, item_stack))
        self.player.send_packet(pk.get_packet_id(), pk.serialize())

    def send_cursor(self):
        if self._closed:
            return
        from endstone_inventoryui._protocol.packets.types import FullContainerName
        item = self.container_manager.cursor_container.actual.get(0)
        pk = InventoryContentPacket(124)
        pk.container_name = FullContainerName(59)
        stack_id = self.container_manager.tracker.assign_slot(59, 0, item)
        pk.items.append(ItemStackWrapper(stack_id, item))
        self.player.send_packet(pk.get_packet_id(), pk.serialize())

    def update_slot(self, slot: int):
        item = self.menu.inventory.get_item(slot)
        stack_id = self.container_manager.assign_virtual_slot(slot, item)
        pk = InventorySlotPacket(self.CONTAINER_ID, slot=slot, item=ItemStackWrapper(stack_id, item))
        self.player.send_packet(pk.get_packet_id(), pk.serialize())

    def close(self, sync_inventory: bool = True, *, send_close: bool = True):
        if self._closed:
            return
        self._closed = True
        self.state = self.State.CLOSING
        self.last_progress = time.monotonic()
        if send_close and self.menu is not None:
            pk = ContainerClosePacket(self.CONTAINER_ID, self.menu.type.container_type, True)
            self.player.send_packet(pk.get_packet_id(), pk.serialize())
        if self.graphic is not None:
            self.graphic.remove(self.player)
        if self.container_manager is not None:
            cursor_item = self.container_manager.cursor_container.get(0)
            if cursor_item is not None:
                leftovers = self.player.inventory.add_item(cursor_item)
                for item in leftovers.values():
                    self.player.dimension.drop_item(self.player.location, item)
                self.container_manager.cursor_container.set(0, None)
            # fix stack id desync between client and BDS
            if sync_inventory:
                self.container_manager.sync_player_inventory()
        if self.menu is not None and self.menu._close_listener is not None:
            self.menu._close_listener(self.player)

    def update_state(self, state: State):
        self.last_progress = time.monotonic()
        self.state = state
        match state:
            case self.State.GRAPHIC_RECEIVED:
                self.send_graphic_data()
            case self.State.GRAPHIC_DATA_RECEIVED:
                self.open()
            case self.State.OPEN:
                self.send_contents()
