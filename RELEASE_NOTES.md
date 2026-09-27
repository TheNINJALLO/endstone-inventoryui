# 2.0.7

InventoryUI now decodes the cereal action discriminator and fixed-width stack IDs used by BDS 1.26.51. Menu opening uses ordered latency acknowledgements, double chests include pairing data, rejected batches receive responses for every request, and close/stop callbacks save while player objects are valid. Item insertion conserves stack counts and rejected drops do not spawn items.

Full custom item NBT now survives transaction cloning. The live BDS runner verifies transfers, page controls, SQLite persistence, and open-menu shutdown; see docs/validation.md.
