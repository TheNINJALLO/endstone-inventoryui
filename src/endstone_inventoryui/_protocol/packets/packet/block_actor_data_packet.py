# Copyright © 2025 GlacieTeam. All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not
# distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

from typing import Optional
from bstream import BinaryStream, ReadOnlyBinaryStream
from rapidnbt import CompoundTag
from endstone_inventoryui._protocol.packets.packet.packet_base import Packet
from endstone_inventoryui._protocol.packets.minecraft_packet_ids import MinecraftPacketIds
from endstone_inventoryui._protocol.packets.types.block_pos import BlockPos


class BlockActorDataPacket(Packet):
    block_position: BlockPos
    actor_data_tags: CompoundTag

    def __init__(
        self,
        pos: Optional[BlockPos] = None,
        nbt: Optional[CompoundTag] = None,
    ):
        super().__init__()
        self.block_position = pos or BlockPos()
        self.actor_data_tags = nbt or CompoundTag()

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.BlockActorData

    def get_packet_name(self) -> str:
        return "BlockActorDataPacket"

    def write(self, stream: BinaryStream) -> None:
        self.block_position.write(stream)
        self.actor_data_tags.serialize(stream)

    def read(self, stream: ReadOnlyBinaryStream) -> None:
        self.block_position.read(stream)
        self.actor_data_tags.deserialize(stream)
