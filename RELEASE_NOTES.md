# 2.0.10 — release, 2026-11-02

Encode the complete native typed NBT tree in item packets, including nested storage-item contents and custom lore. Verify NBT while cloning and fail before a lossy transfer. Add `Menu.set_commit_listener`: storage plugins can checkpoint after staged slots apply and before acknowledgement; an exception restores changed player/menu/cursor slots. Callbacks must avoid irreversible side effects. Flush menu/cursor state at LOWEST quit priority before Inventory Share captures it.

# 2.0.7

InventoryUI now decodes the cereal action discriminator and fixed-width stack IDs used by BDS 1.26.51. Menu opening uses ordered latency acknowledgements, double chests include pairing data, rejected batches receive responses for every request, and close/stop callbacks save while player objects are valid. Item insertion conserves stack counts and rejected drops do not spawn items.

Full custom item NBT now survives transaction cloning. The live BDS runner verifies transfers, page controls, SQLite persistence, and open-menu shutdown; see docs/validation.md.
