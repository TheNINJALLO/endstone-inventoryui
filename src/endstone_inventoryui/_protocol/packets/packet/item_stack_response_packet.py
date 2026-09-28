# Copyright © 2025 GlacieTeam. All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not
# distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

from typing import List
from bstream import BinaryStream, ReadOnlyBinaryStream
from endstone_inventoryui._protocol.packets.minecraft_packet_ids import MinecraftPacketIds
from endstone_inventoryui._protocol.packets.packet.packet_base import Packet
from endstone_inventoryui._protocol.packets.types.item_stack_response import (
    ItemStackResponse
)


class ItemStackResponsePacket(Packet):
    responses: List[ItemStackResponse]

    def __init__(self, responses: List[ItemStackResponse] | None = None):
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
        self.responses = []
        for _ in range(count):
            response = ItemStackResponse()
            response.read(stream)
            self.responses.append(response)