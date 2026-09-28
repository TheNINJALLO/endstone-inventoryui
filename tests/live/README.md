# Inventory interaction acceptance test

The Windows runner starts a disposable BDS 1.26.51.1 server with Endstone 0.11.11, InventoryUI, Backpacks, Inventory Manager, and a test probe. It requires the supplied server fixture at `endstone-paradox/scratch/servers/windows` and the Windows Endstone environment. It does not connect to a production server.

Build the pinned Gophertunnel 1.62.0 client using Go 1.26.0 from `tests/live/client`, placing the executable at `scratch/client/bedrock-inventory-client.exe`:

```powershell
go build -o ../../../scratch/client/bedrock-inventory-client.exe .
```

From the workspace containing the plugin repositories:

```powershell
& endstone-paradox/scratch/windows-runtime-venv/Scripts/python.exe endstone-inventoryui-main/tests/live/run_windows.py --workspace . --run backpack-air --interaction air --tier gigantic
& endstone-paradox/scratch/windows-runtime-venv/Scripts/python.exe endstone-inventoryui-main/tests/live/run_windows.py --workspace . --run backpack-block-legacy --interaction block --tier gigantic --legacy-material
```

Use a new `--run` name each time. Add `--wheel-dir <directory>` to test built wheels instead of source. The directory should contain exactly one wheel for each of InventoryUI, Backpacks, and Inventory Manager. Repeat `air` and `block` for tiers `small`, `large`, and `gigantic`. `--legacy-material` exercises the old gigantic `shulker_box` configuration. `--vault` retains the virtual vault transfer test.

The client waits for a real in-world spawn, selects the server-issued item with `MobEquipment`, and sends a `PlayerAuthInput` use-item interaction. The probe records the resulting `PlayerInteractEvent`; physical interaction tests never call the backpack open method directly. The probe sends an initial inventory snapshot because this protocol client does not implement a retail inventory screen controller.

Assertions cover the open acknowledgement, decoded contents, deposit/withdrawal, pagination where supported, metadata, SQLite close/reopen, and final save during shutdown. Results record wheel hashes and only mark success after shutdown verification. Packet violation warnings fail the run. The non-interaction and vault modes call the manager directly and do not cover the item handler.

This is a protocol integration test. A latency acknowledgement does not prove a retail client rendered the chest screen; touch/controller input and visual presentation require a retail device test.
