# 2.0.8 startup validation

Reproduced the reported `NetworkStackLatencyPacket` import failure on **Linux / Python 3.14.7 / Endstone 0.11.12** by installing `bedrock-protocol-packets-ng==0.0.9`, then `bedrock-protocol-packets==0.0.7`. InventoryUI 2.0.7 fails before registration; 2.0.8 imports and runs with both conflicting distributions still installed.

- **51 combined InventoryUI/Backpacks tests passed** on Windows/Python 3.11 and on Linux/Python 3.14. The Linux tests exercise the built wheels in the conflicting environment. Import isolation tests also block access to the shared protocol entirely.
- On Linux / Endstone 0.11.12 / BDS 1.26.51.1, live air and block backpack interactions pass with transfers, gigantic page buttons, custom NBT, SQLite close/reopen, and shutdown saving. Virtual vault/cursor transfers pass and conserve item totals.
- A Windows / Endstone 0.11.11 / Python 3.11 live air-interaction regression also passes.
- BlockData 0.6.6's complete Linux wheel loads its native provider alongside InventoryUI without a duplicate-provider warning. No separate BlockData `.so` is installed in these tests.
- Release CI tests clean installs and the conflicting shared packages on both Python 3.11 and 3.14, and waits for both before publishing.

All three tagged releases passed GitHub Actions. The downloaded InventoryUI 2.0.8, Backpacks 1.0.93, and Inventory Manager 1.0.17 wheels also passed the full live Linux/Python 3.14 legacy-item scenario with the conflicting packages and BlockData bundle installed. Their 83 Python modules match the tested local builds by AST comparison; published hashes are recorded with the results.

See [results and hashes](validation/2.0.8.json), [startup instructions](startup.md), and [reproduction guide](../tests/live/README.md). These are protocol integration tests, not retail-device visual tests. The earlier Windows-only coverage did not exercise conflicting package installations.

## Earlier 2.0.7 validation

BDS 1.26.51.1 / Endstone 0.11.11 / Windows x64 / Python 3.11, using an independently encoded Gophertunnel 1.62.0 client (protocol 2193).

- Menu opens through the latency acknowledgement without a packet violation warning.
- Named items retain full custom NBT while depositing, withdrawing, saving to SQLite, and reopening.
- Next/previous page actions preserve contents.
- Server stop with a menu open saves the last transfer and exits normally.
- Virtual vault deposits consume the requested source amount; withdrawals and pagination preserve the total across storage and player inventory.

The reproducible runner and client are in [InventoryUI tests/live](https://github.com/TheNINJALLO/endstone-inventoryui/tree/v2.0.7/tests/live). The runner creates disposable offline servers; it requires the supplied Windows BDS fixture and pinned client. This is a protocol integration test, not a retail-client visual test or a production rollout.

## Backpack item interactions

The original 2.0.7 tests opened storage directly through the backpack manager, leaving the item interaction handler untested. The expanded [runner](../tests/live/README.md) selects an assigned item and sends real air/block interactions after the player has spawned inside the world. It covers each default backpack tier and the legacy shulker material name, with transfers, supported page actions, close/reopen, and shutdown persistence.

Backpacks 1.0.91 rejected `white_shulker_box` items when its gigantic tier was configured as `shulker_box`, before calling InventoryUI. Backpacks 1.0.92 resolves that mismatch. The repair and its results are documented in [Backpacks validation](https://github.com/TheNINJALLO/endstone-ninjos-backpacks/blob/main/docs/validation.md). These test changes do not modify InventoryUI's 2.0.7 runtime. Protocol acknowledgements do not establish that a retail client rendered the screen.
