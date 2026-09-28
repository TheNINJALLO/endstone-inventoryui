# 2.0.7 validation

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
