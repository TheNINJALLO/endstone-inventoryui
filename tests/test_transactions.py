from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bedrock_protocol.packets.enums import ItemStackRequestActionType as Action

from endstone_inventoryui.listener import EventListener
from endstone_inventoryui.manager.container.container_manager import ContainerManager
from endstone_inventoryui.network.item_stack_request_packet import ItemStackRequestSlotInfo
from bedrock_protocol.packets.types import FullContainerName


class Item:
    def __init__(self, name="minecraft:air", amount=1):
        self.type = SimpleNamespace(id=name)
        self.amount, self.data, self.max_stack_size, self.item_meta = amount, 0, 64, None


class Inventory:
    def __init__(self):
        self.slots = {}

    def get_item(self, slot):
        return self.slots.get(slot)

    def set_item(self, slot, item):
        self.slots[slot] = item

    def clear(self, slot):
        self.slots.pop(slot, None)


def slot(container, index):
    return ItemStackRequestSlotInfo(FullContainerName(container), index)


@pytest.fixture
def manager(monkeypatch):
    import endstone_inventoryui.manager.container.container_manager as cm
    import endstone_inventoryui.manager.container.transaction_container as tc
    import endstone_inventoryui.util.item_utils as utils
    for module in (cm, tc, utils):
        monkeypatch.setattr(module, "clone_item", deepcopy)
    monkeypatch.setattr(cm, "ItemStack", Item)
    monkeypatch.setattr(cm, "can_stack", lambda a, b: a.type.id == b.type.id)
    player = SimpleNamespace(inventory=Inventory(), dimension=SimpleNamespace(drop_item=Mock()), location=object())
    return ContainerManager(player, Inventory())


def test_deposit_and_withdraw_commit_both_sides(manager):
    manager.player.inventory.set_item(0, Item("minecraft:diamond", 12))
    manager.begin_request(-1)
    manager.transfer_items(slot(12, 0), slot(7, 4), 5)
    manager.commit_transaction()
    assert manager.player.inventory.get_item(0).amount == 7
    assert manager.virtual_container.actual.get(4).amount == 5
    manager.begin_request(-3)
    manager.transfer_items(slot(7, 4), slot(12, 0), 5)
    manager.commit_transaction()
    assert manager.player.inventory.get_item(0).amount == 12
    assert manager.virtual_container.actual.get(4) is None


def test_rejected_request_does_not_spawn_a_drop(manager):
    manager.player.inventory.set_item(0, Item("minecraft:diamond", 12))
    manager.begin_request(-1)
    manager.handle_drop(slot(12, 0), 5)
    manager.discard_transaction()
    manager.player.dimension.drop_item.assert_not_called()
    assert manager.player.inventory.get_item(0).amount == 12


def test_overfull_merge_can_be_discarded_without_losing_items(manager):
    manager.player.inventory.set_item(0, Item("minecraft:diamond", 12))
    manager.virtual_container.actual.set(4, Item("minecraft:diamond", 60))
    manager.begin_request(-1)
    with pytest.raises(ValueError, match="stack limit"):
        manager.transfer_items(slot(12, 0), slot(7, 4), 5)
    manager.discard_transaction()
    assert manager.player.inventory.get_item(0).amount == 12
    assert manager.virtual_container.actual.get(4).amount == 60


def test_rejected_button_still_responds_to_every_request_in_batch(manager):
    listener = EventListener(SimpleNamespace(logger=Mock()))
    listener._apply_menu_action = Mock(return_value=False)
    listener._send_item_stack_responses = Mock()
    action = SimpleNamespace(action_type=Action.Take,
                             action_data=SimpleNamespace(source=slot(7, 53), distination=slot(59, 0), amount=1))
    requests = [SimpleNamespace(client_request_id=i, request_actions=[action]) for i in (-1, -3)]
    listener._handle_item_stack_request(manager.player, SimpleNamespace(container_manager=manager),
                                       object(), SimpleNamespace(request=SimpleNamespace(request_data=requests)))
    responses = listener._send_item_stack_responses.call_args.args[1]
    assert [r.request_id for r in responses] == [-1, -3]
    assert all(r.result == r.RESULT_ERROR for r in responses)


def test_menu_add_item_conserves_items_and_notifies(monkeypatch):
    import endstone_inventoryui.menu.inventory as module
    monkeypatch.setattr(module, "clone_item", deepcopy)
    monkeypatch.setattr(Item, "is_similar", lambda a, b: a.type.id == b.type.id, raising=False)
    changed = []
    inv = module.MenuInventory(size=2, slot_updated=changed.append)
    inv.set_item(0, Item("minecraft:diamond", 60))
    source = Item("minecraft:diamond", 4)
    assert inv.add_item(source) == {}
    assert inv.contents[0].amount == 64 and inv.contents[1] is None
    assert source.amount == 4
    changed.clear()
    assert inv.add_item(Item("minecraft:diamond", 64)) == {}
    assert changed == [1]
    assert inv.add_item(Item("minecraft:diamond", 5))[0].amount == 5
