"""A server's shared protocol installation must not control InventoryUI imports."""

import subprocess
import sys


def test_plugin_loads_without_any_shared_protocol_package():
    code = '''
import importlib.abc
import sys

class RejectSharedProtocol(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "bedrock_protocol" or fullname.startswith("bedrock_protocol."):
            raise AssertionError("InventoryUI accessed the shared protocol: " + fullname)

sys.meta_path.insert(0, RejectSharedProtocol())
from endstone_inventoryui import InventoryUIPlugin, Menu, MenuType
from endstone_inventoryui._protocol.packets.packet import NetworkStackLatencyPacket
assert MenuType.DOUBLE_CHEST.container_size == 54
assert NetworkStackLatencyPacket(123, True).serialize() == bytes.fromhex("7b0000000000000001")
assert not any(n == "bedrock_protocol" or n.startswith("bedrock_protocol.") for n in sys.modules)
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
