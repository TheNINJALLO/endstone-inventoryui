# InventoryUI startup failures

If the log contains `ImportError: cannot import name 'NetworkStackLatencyPacket'`, InventoryUI has failed before it can register menus. Backpacks cannot open until InventoryUI loads successfully.

The original `bedrock-protocol-packets` 0.0.7 and `bedrock-protocol-packets-ng` 0.0.9 packages write to the same Python module directory. Installing the original package last reproduces this exact error on Linux with Python 3.14, even though both distributions appear installed. Reinstalling them in a different order is not a lasting fix.

InventoryUI **2.0.8** keeps its protocol helpers under `endstone_inventoryui._protocol`, so other plugins cannot overwrite those imports by installing either shared package. It does not edit the shared package or register global module aliases.

1. Stop the server.
2. Replace InventoryUI with **2.0.8**. If installed, replace Backpacks with **1.0.93** and Inventory Manager with **1.0.17** so their dependency pins select the same InventoryUI release.
3. Keep one wheel per plugin and preserve the plugin data folders. Do not delete the shared Python packages or `plugins/.local`; other plugins may need them.
4. Restart and confirm InventoryUI enables at **2.0.8**, with no import traceback.

## BlockData provider warning

`Plugin 'blockdata_inspector' provides 'blockdata_api', which is the name of another plugin` is a separate dependency-name warning. It means Endstone discovered a native `blockdata_api` candidate alongside the inspector's compatibility alias; it is not the InventoryUI import failure.

For **BlockData 0.6.6**, use the matching **CPython 3.14 Linux x64 inspector wheel** alone in `plugins/`. That wheel contains and loads the matching native provider. While stopped, move any separately installed BlockData native `.so` out of `plugins/` and its scanned subdirectories. Keep databases and data folders. Bundle-only startup was tested with Endstone **0.11.12** / BDS **1.26.51.1** and produced no duplicate-provider warning.

The `provides` alias is needed for dependency ordering when loading from the wheel alone. Removing it from the source can prevent dependent plugins from loading. Follow the [BlockData installation guide](https://github.com/TheNINJALLO/endstone-blockdata-api/blob/main/docs/INSTALL.md).
