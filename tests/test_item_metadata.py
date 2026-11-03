from types import SimpleNamespace
import json

import pytest
from endstone.nbt import CompoundTag, ListTag, StringTag, ByteTag, IntTag
from endstone_inventoryui.util.item_utils import build_item_tag


def test_wire_metadata_preserves_nested_bundle_and_custom_lore():
    raw = CompoundTag({'storage_item_component_content': ListTag([
        CompoundTag({'Name': StringTag('minecraft:diamond'), 'Count': ByteTag(7),
                     'tag': CompoundTag({'display': CompoundTag({'Lore': ListTag([StringTag('§dEssentials lore')])})})})
    ]), 'bundle_weight': IntTag(7), 'custom_marker': StringTag('preserve me')})
    item = SimpleNamespace(nbt=raw)
    wire = build_item_tag(item)
    assert wire.get('custom_marker').value.decode('utf-8') == 'preserve me'
    assert wire.get('bundle_weight').value == 7
    saved = json.loads(wire.to_json())
    assert saved['storage_item_component_content'][0]['Count'] == 7
    lore = saved['storage_item_component_content'][0]['tag']['display']['Lore'][0]
    assert lore == '§dEssentials lore'


def test_unknown_metadata_cannot_silently_disappear_from_wire():
    with pytest.raises(ValueError):
        build_item_tag(SimpleNamespace(nbt=object()))
