from types import SimpleNamespace

from bedrock_protocol.packets.enums import ItemStackRequestActionType
from bedrock_protocol.packets.types import FullContainerName
from bstream import BinaryStream, ReadOnlyBinaryStream

from endstone_inventoryui.listener import EventListener
from endstone_inventoryui.network.item_stack_request_packet import ItemStackRequestPacket
from endstone_inventoryui.network.item_stack_response_packet import (
    ItemStackResponse,
    ItemStackResponseContainerInfo,
    ItemStackResponsePacket,
    ItemStackResponseSlotInfo,
)
from endstone_inventoryui.network.item_stack_wrapper import ItemStackWrapper


class RecordingStream:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if not name.startswith("write_"):
            raise AttributeError(name)

        def record(value):
            self.calls.append((name, value))

        return record


def test_inventory_descriptor_uses_single_network_id_varint(monkeypatch):
    wrapper = ItemStackWrapper.__new__(ItemStackWrapper)
    wrapper.stack_id = 42
    wrapper.item_stack = SimpleNamespace(amount=3, data=7)
    wrapper.data = SimpleNamespace(item_id=5)
    wrapper.write_footer = lambda stream: None
    monkeypatch.setattr(
        "endstone_inventoryui.network.item_stack_wrapper.item_utils.is_air",
        lambda item: False,
    )

    stream = RecordingStream()
    wrapper.write_descriptor(stream)

    assert stream.calls[:7] == [
        ("write_signed_short", 5),
        ("write_unsigned_short", 3),
        ("write_unsigned_varint", 7),
        ("write_bool", True),
        ("write_varint", 42),
        ("write_unsigned_varint", 0),
        ("write_bytes", b""),
    ]


def test_item_stack_response_writes_protocol_2169_optionals():
    response = ItemStackResponse(
        result=ItemStackResponse.RESULT_OK,
        request_id=-1,
        container_infos=[
            ItemStackResponseContainerInfo(
                container=FullContainerName(21),
                slots=[
                    ItemStackResponseSlotInfo(
                        slot=4,
                        hotbar_slot=4,
                        count=0,
                        item_stack_id=99,
                    )
                ],
            )
        ],
    )
    payload = ItemStackResponsePacket([response]).serialize()

    stream = ReadOnlyBinaryStream(payload)
    assert stream.get_unsigned_varint() == 1
    assert stream.get_byte() == ItemStackResponse.RESULT_OK
    assert stream.get_varint() == -1
    assert stream.get_bool() is True  # Containers optional
    assert stream.get_unsigned_varint() == 1
    container = FullContainerName()
    container.read(stream)
    assert container.container_enum == 21
    assert stream.get_unsigned_varint() == 1
    assert stream.get_byte() == 4
    assert stream.get_byte() == 4
    assert stream.get_byte() == 0
    assert stream.get_bool() is False  # Empty slot has no network ID value
    assert stream.get_string() == ""
    assert stream.get_bool() is False  # No redacted custom name
    assert stream.get_varint() == 0
    assert stream.get_left_buffer() == b""


def test_item_stack_request_reads_tagged_network_id_variants():
    stream = BinaryStream()
    stream.write_unsigned_varint(1)  # Requests
    stream.write_varint(-1)
    stream.write_unsigned_varint(1)  # Actions
    stream.write_byte(int(ItemStackRequestActionType.Take))
    stream.write_byte(1)

    FullContainerName(21).write(stream)
    stream.write_byte(4)
    stream.write_unsigned_varint(0)  # Server network ID alternative
    stream.write_varint(42)

    FullContainerName(12).write(stream)
    stream.write_byte(7)
    stream.write_unsigned_varint(0)
    stream.write_varint(84)

    stream.write_unsigned_varint(0)  # Strings to filter
    stream.write_signed_int(0)

    packet = ItemStackRequestPacket()
    packet.deserialize(stream.get_and_release_data())
    request = packet.request.request_data[0]
    action = request.request_actions[0]

    assert request.client_request_id == -1
    assert action.action_type == ItemStackRequestActionType.Take
    assert action.action_data.source.slot == 4
    assert action.action_data.source.net_id_variant == 0
    assert action.action_data.source.net_id == 42
    assert action.action_data.distination.slot == 7
    assert action.action_data.distination.net_id == 84


def test_latency_timestamp_matching_is_exact_but_scale_tolerant():
    assert EventListener._timestamps_match(123, 123)
    assert EventListener._timestamps_match(123_000_000, 123)
    assert EventListener._timestamps_match(123, 123_000)
    assert not EventListener._timestamps_match(123_000_000, 124)
    assert not EventListener._timestamps_match(0, 0)
