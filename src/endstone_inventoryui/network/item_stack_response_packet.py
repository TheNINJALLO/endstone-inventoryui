"""Protocol 2169 ItemStackResponse encoder used by virtual inventories."""

from dataclasses import dataclass, field

from bedrock_protocol.packets.minecraft_packet_ids import MinecraftPacketIds
from bedrock_protocol.packets.packet.packet_base import Packet
from bedrock_protocol.packets.types import FullContainerName
from bstream import BinaryStream, ReadOnlyBinaryStream


@dataclass
class ItemStackResponseSlotInfo:
    slot: int = 0
    hotbar_slot: int = 0
    count: int = 0
    item_stack_id: int = 0
    custom_name: str = ""
    filtered_custom_name: str = ""
    durability_correction: int = 0

    def write(self, stream: BinaryStream) -> None:
        stream.write_byte(self.slot)
        stream.write_byte(self.hotbar_slot)
        stream.write_byte(self.count)

        # Item Stack Net Id is a protocol-2169 optional.  Its presence byte is
        # mandatory, but its value is only present for non-empty stacks.
        has_stack_id = self.count > 0
        stream.write_bool(has_stack_id)
        if has_stack_id:
            stream.write_varint(self.item_stack_id)

        # Bedrock::Safety::RedactableString contains a required unredacted
        # string and an optional redacted value.
        stream.write_string(self.custom_name)
        has_filtered_name = bool(
            self.filtered_custom_name
            and self.filtered_custom_name != self.custom_name
        )
        stream.write_bool(has_filtered_name)
        if has_filtered_name:
            stream.write_string(self.filtered_custom_name)

        stream.write_varint(self.durability_correction)

    @classmethod
    def read_from(cls, stream: ReadOnlyBinaryStream) -> "ItemStackResponseSlotInfo":
        slot = stream.get_byte()
        hotbar_slot = stream.get_byte()
        count = stream.get_byte()
        item_stack_id = stream.get_varint() if stream.get_bool() else 0
        custom_name = stream.get_string()
        filtered_custom_name = stream.get_string() if stream.get_bool() else ""
        durability_correction = stream.get_varint()
        return cls(
            slot,
            hotbar_slot,
            count,
            item_stack_id,
            custom_name,
            filtered_custom_name,
            durability_correction,
        )


@dataclass
class ItemStackResponseContainerInfo:
    container: FullContainerName = field(default_factory=FullContainerName)
    slots: list[ItemStackResponseSlotInfo] = field(default_factory=list)

    def write(self, stream: BinaryStream) -> None:
        self.container.write(stream)
        stream.write_unsigned_varint(len(self.slots))
        for slot in self.slots:
            slot.write(stream)

    @classmethod
    def read_from(cls, stream: ReadOnlyBinaryStream) -> "ItemStackResponseContainerInfo":
        container = FullContainerName()
        container.read(stream)
        slot_count = stream.get_unsigned_varint()
        return cls(
            container,
            [ItemStackResponseSlotInfo.read_from(stream) for _ in range(slot_count)],
        )


@dataclass
class ItemStackResponse:
    RESULT_OK = 0
    RESULT_ERROR = 1

    result: int = RESULT_OK
    request_id: int = 0
    container_infos: list[ItemStackResponseContainerInfo] = field(default_factory=list)

    def write(self, stream: BinaryStream) -> None:
        stream.write_byte(self.result)
        stream.write_varint(self.request_id)

        # Containers became an explicit cereal optional in protocol 2169.
        has_containers = self.result == self.RESULT_OK
        stream.write_bool(has_containers)
        if has_containers:
            stream.write_unsigned_varint(len(self.container_infos))
            for container_info in self.container_infos:
                container_info.write(stream)

    @classmethod
    def read_from(cls, stream: ReadOnlyBinaryStream) -> "ItemStackResponse":
        result = stream.get_byte()
        request_id = stream.get_varint()
        has_containers = stream.get_bool()
        container_infos: list[ItemStackResponseContainerInfo] = []
        if has_containers:
            count = stream.get_unsigned_varint()
            container_infos = [
                ItemStackResponseContainerInfo.read_from(stream)
                for _ in range(count)
            ]
        return cls(result, request_id, container_infos)


class ItemStackResponsePacket(Packet):
    def __init__(self, responses: list[ItemStackResponse] | None = None):
        super().__init__()
        self.responses = responses or []

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.ItemStackResponse

    def get_packet_name(self) -> str:
        return "ItemStackResponse"

    def write(self, stream: BinaryStream) -> None:
        stream.write_unsigned_varint(len(self.responses))
        for response in self.responses:
            response.write(stream)

    def read(self, stream: ReadOnlyBinaryStream) -> None:
        count = stream.get_unsigned_varint()
        self.responses = [ItemStackResponse.read_from(stream) for _ in range(count)]
