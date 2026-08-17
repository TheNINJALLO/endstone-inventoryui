"""Protocol 2169 ItemStackRequest decoder.

The upstream ``bedrock-protocol-packets-ng`` 0.0.9 decoder targets the
pre-1.26.44 request layout.  BDS 1.26.44 moved request slot network IDs to a
tagged cereal variant, so InventoryUI owns this small decoder until the shared
packet package exposes the new layout.
"""

from dataclasses import dataclass, field

from bedrock_protocol.packets.enums import ItemStackRequestActionType
from bedrock_protocol.packets.minecraft_packet_ids import MinecraftPacketIds
from bedrock_protocol.packets.packet.packet_base import Packet
from bedrock_protocol.packets.types import FullContainerName
from bstream import BinaryStream, ReadOnlyBinaryStream


class UnsupportedItemStackRequestAction(ValueError):
    def __init__(self, request_id: int, action_type: int):
        super().__init__(f"Unsupported item stack request action: {action_type}")
        self.request_id = request_id
        self.action_type = action_type


@dataclass
class ItemStackRequestSlotInfo:
    container: FullContainerName = field(default_factory=FullContainerName)
    slot: int = 0
    net_id: int = 0
    net_id_variant: int = 0

    @classmethod
    def read_from(cls, stream: ReadOnlyBinaryStream) -> "ItemStackRequestSlotInfo":
        container = FullContainerName()
        container.read(stream)
        slot = stream.get_byte()

        # Protocol 2169 uses cereal's tagged variant here.  The variant index
        # distinguishes server, client-request, and legacy-client-request IDs;
        # all three alternatives carry a compressed signed 32-bit ID.
        net_id_variant = stream.get_unsigned_varint()
        if net_id_variant > 2:
            raise ValueError(f"Invalid item stack net ID variant: {net_id_variant}")
        net_id = stream.get_varint()
        return cls(container, slot, net_id, net_id_variant)

    def write(self, stream: BinaryStream) -> None:
        self.container.write(stream)
        stream.write_byte(self.slot)
        stream.write_unsigned_varint(self.net_id_variant)
        stream.write_varint(self.net_id)


@dataclass
class ItemStackRequestActionData:
    amount: int = 0
    source: ItemStackRequestSlotInfo = field(default_factory=ItemStackRequestSlotInfo)
    distination: ItemStackRequestSlotInfo = field(default_factory=ItemStackRequestSlotInfo)
    randomly: bool = False


@dataclass
class ItemStackRequestAction:
    action_type: ItemStackRequestActionType
    action_data: ItemStackRequestActionData

    @classmethod
    def read_from(
        cls,
        stream: ReadOnlyBinaryStream,
        request_id: int,
    ) -> "ItemStackRequestAction":
        action_value = stream.get_byte()
        try:
            action_type = ItemStackRequestActionType(action_value)
        except ValueError as error:
            raise UnsupportedItemStackRequestAction(request_id, action_value) from error

        supported = {
            ItemStackRequestActionType.Take,
            ItemStackRequestActionType.Place,
            ItemStackRequestActionType.Swap,
            ItemStackRequestActionType.Drop,
        }
        if action_type not in supported:
            raise UnsupportedItemStackRequestAction(request_id, action_value)

        amount = 0 if action_type == ItemStackRequestActionType.Swap else stream.get_byte()
        source = ItemStackRequestSlotInfo.read_from(stream)
        destination = ItemStackRequestSlotInfo()
        randomly = False

        if action_type == ItemStackRequestActionType.Drop:
            # The reflected 2169 Drop action includes this trailing flag.
            randomly = stream.get_bool()
        else:
            destination = ItemStackRequestSlotInfo.read_from(stream)

        return cls(
            action_type,
            ItemStackRequestActionData(amount, source, destination, randomly),
        )

    def write(self, stream: BinaryStream) -> None:
        stream.write_byte(int(self.action_type))
        if self.action_type != ItemStackRequestActionType.Swap:
            stream.write_byte(self.action_data.amount)
        self.action_data.source.write(stream)
        if self.action_type == ItemStackRequestActionType.Drop:
            stream.write_bool(self.action_data.randomly)
        else:
            self.action_data.distination.write(stream)


@dataclass
class ItemStackRequestData:
    client_request_id: int = 0
    request_actions: list[ItemStackRequestAction] = field(default_factory=list)
    strings_to_filter: list[str] = field(default_factory=list)
    strings_to_filter_origin: int = 0

    @classmethod
    def read_from(cls, stream: ReadOnlyBinaryStream) -> "ItemStackRequestData":
        request_id = stream.get_varint()
        action_count = stream.get_unsigned_varint()
        if not 1 <= action_count <= 100:
            raise ValueError(f"Invalid item stack request action count: {action_count}")
        actions = [
            ItemStackRequestAction.read_from(stream, request_id)
            for _ in range(action_count)
        ]

        string_count = stream.get_unsigned_varint()
        if string_count > 100:
            raise ValueError(f"Invalid item stack request string count: {string_count}")
        strings = [stream.get_string() for _ in range(string_count)]
        origin = stream.get_signed_int()
        return cls(request_id, actions, strings, origin)

    def write(self, stream: BinaryStream) -> None:
        stream.write_varint(self.client_request_id)
        stream.write_unsigned_varint(len(self.request_actions))
        for action in self.request_actions:
            action.write(stream)
        stream.write_unsigned_varint(len(self.strings_to_filter))
        for value in self.strings_to_filter:
            stream.write_string(value)
        stream.write_signed_int(self.strings_to_filter_origin)


@dataclass
class ItemStackRequest:
    request_data: list[ItemStackRequestData] = field(default_factory=list)


class ItemStackRequestPacket(Packet):
    def __init__(self, request: ItemStackRequest | None = None):
        super().__init__()
        self.request = request or ItemStackRequest()

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.ItemStackRequest

    def get_packet_name(self) -> str:
        return "ItemStackRequest"

    def write(self, stream: BinaryStream) -> None:
        stream.write_unsigned_varint(len(self.request.request_data))
        for request in self.request.request_data:
            request.write(stream)

    def read(self, stream: ReadOnlyBinaryStream) -> None:
        request_count = stream.get_unsigned_varint()
        if request_count > 100:
            raise ValueError(f"Invalid item stack request count: {request_count}")
        self.request = ItemStackRequest([
            ItemStackRequestData.read_from(stream)
            for _ in range(request_count)
        ])
