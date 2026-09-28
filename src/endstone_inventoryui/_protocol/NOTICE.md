# Private protocol primitives

Vendored from `bedrock-protocol-packets-ng` 0.0.9, published by Shock95:
https://github.com/Shock95/bedrock-protocol-packets-ng
https://pypi.org/project/bedrock-protocol-packets-ng/0.0.9/

These files retain their upstream Mozilla Public License 2.0 headers; the full
license is included in LICENSE. Modifications: imports point to
`endstone_inventoryui._protocol` instead of the shared `bedrock_protocol`
namespace. InventoryUI's current inventory request/response codecs remain in
`endstone_inventoryui.network` and override the older wire formats.

This private copy prevents another plugin's installation of the original
`bedrock-protocol-packets` package from overwriting InventoryUI's imports.
It does not register aliases in sys.modules or change other plugins' packages.

Source and modifications are included in the wheel and source repository.
