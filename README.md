<!-- endstone-professional-header:start -->
<p align="center">
  <img src="docs/assets/banner.svg" width="100%" alt="Endstone InventoryUI &mdash; Inventory UI plugin for Endstone servers">
</p>

<p align="center">
  <a href="https://github.com/TheNINJALLO/endstone-inventoryui/actions/workflows/wheel-release.yml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/TheNINJALLO/endstone-inventoryui/wheel-release.yml?branch=main&amp;style=for-the-badge&amp;logo=githubactions&amp;logoColor=white&amp;label=Build"></a>
  <a href="https://github.com/TheNINJALLO/endstone-inventoryui/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/TheNINJALLO/endstone-inventoryui?display_name=tag&amp;style=for-the-badge&amp;label=Release"></a>
</p>

<p align="center">
  <img alt="Endstone 0.11.11 / 0.11.12" src="https://img.shields.io/badge/Endstone-0.11.12-52b7a8?style=flat-square">
  <img alt="API 0.11" src="https://img.shields.io/badge/API-0.11-63b8ff?style=flat-square">
  <img alt="BDS 1.26.51" src="https://img.shields.io/badge/BDS-1.26.51-8b7dff?style=flat-square">
  <img alt="Python >=3.11" src="https://img.shields.io/badge/Python-%3E=3.11-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white">
</p>

<p align="center">
  <strong>Inventory UI plugin for Endstone servers.</strong>
</p>

<p align="center">
  <a href="#what-it-does">What it does</a> &bull;
  <a href="#how-to-use">How to use</a> &bull;
  <a href="#commands-and-permissions">Commands</a> &bull;
  <a href="#install">Install</a> &bull;
  <a href="https://github.com/TheNINJALLO/endstone-inventoryui/releases">Releases</a>
</p>

## Overview

Inventory UI plugin for Endstone servers. This release is aligned with Endstone 0.11.11 / 0.11.12 and Minecraft Bedrock Dedicated Server 1.26.51, and is distributed as a Python wheel for direct installation in an Endstone server.

## What it does

- Provides a reusable chest, double-chest, dispenser, and hopper menu API for other Endstone plugins.
- Translates Bedrock inventory packets into safe `MenuTransaction` callbacks.
- Supports click, open, close, queueing, proceed, and discard behavior for custom interfaces.

## How to use

1. Install the wheel as a dependency on every server that runs an InventoryUI-based plugin.
2. From plugin code, create a `Menu`, populate `menu.inventory`, and attach a transaction listener.
3. Call `menu.send_to(player)` to open it and return `proceed()` or `discard()` from each click handler.
4. Use the included `example/` project as the reference implementation.

## Commands and permissions

InventoryUI is a developer API and intentionally registers no player commands. Other plugins import `Menu`, `MenuType`, and `MenuTransaction` and decide how their menus are opened.

## Compatibility

| Component | Supported version |
|---|---|
| Endstone | `0.11.11 / 0.11.12` |
| Endstone API | `0.11` |
| Bedrock Dedicated Server | `1.26.51` |
| Python | `>=3.11` |
| Plugin release | `v2.0.8` |

## Install

Download [the `v2.0.8` wheel over HTTPS](https://github.com/TheNINJALLO/endstone-inventoryui/releases/download/v2.0.8/endstone_inventoryui-2.0.8-py3-none-any.whl).

Copy the downloaded wheel into the server's `plugins/` directory, remove any older wheel for the same plugin, and restart Endstone.

> [!IMPORTANT]
> Use Endstone `0.11.11 / 0.11.12` with BDS `1.26.51`. Back up worlds and plugin data before upgrading a production server.

> [!NOTE]
> `v2.0.8` keeps the inventory layout introduced for BDS `1.26.40`; Endstone 0.11.11 / 0.11.12 confirms BDS `1.26.51` did not change the network protocol. Earlier InventoryUI wheels can send the retired item-stack network-ID layout and disconnect a player when a virtual inventory opens.

## Configuration and secrets

Runtime databases, logs, local `.env` files, server directories, and root `config.toml` files are excluded from source releases. When an example configuration is provided, copy it locally and keep live tokens, passwords, webhook URLs, and server identifiers out of Git.

## Release automation

Every `v*` tag runs [the wheel release workflow](.github/workflows/wheel-release.yml), builds the package in a clean GitHub runner, stores the wheel as a workflow artifact, and attaches it to the matching GitHub release.
<!-- endstone-professional-header:end -->

## 2.0.8 startup repair

InventoryUI now bundles its protocol helpers in a private package. The original `bedrock-protocol-packets` and `bedrock-protocol-packets-ng` distributions share the `bedrock_protocol` namespace; installing one over the other can remove exports such as `NetworkStackLatencyPacket` and prevent InventoryUI from loading. This release works independently of either shared package and needs no startup patch from Backpacks.

Use Backpacks **1.0.93** and Inventory Manager **1.0.17** when those plugins are installed, so their dependencies select InventoryUI **2.0.8**. Replace old wheels while the server is stopped and preserve plugin data. See [startup troubleshooting](docs/startup.md) and [validation](docs/validation.md).

The bundled protocol source retains its MPL-2.0 license; see [third-party notice](src/endstone_inventoryui/_protocol/NOTICE.md). InventoryUI's own code remains MIT licensed.

---

## Project guide

Virtual inventory plugin for Endstone

## API

### MenuType

Enum for menu container types:

- `MenuType.CHEST` â€” single chest (27 slots)
- `MenuType.DOUBLE_CHEST` â€” double chest (54 slots)
- `MenuType.DISPENSER` â€” dispenser (9 slots)
- `MenuType.HOPPER` â€” hopper (5 slots)

### Menu

```python
Menu(type: MenuType, name: str = "")
```

**Properties:**

- `inventory` â€” the `MenuInventory` instance for this menu. Implements an API similar to Endstone's `Inventory`.
- `name` â€” display name shown at the top of the menu
- `type` â€” the `MenuType` used to create this menu

**Methods:**

- `set_name(name: str)` â€” set the display name
- `set_listener(listener)` â€” set the click callback (see [MenuTransaction](#menutransaction))
- `set_open_listener(listener)` â€” callback when a player opens the menu: `(player: Player) -> None`
- `set_close_listener(listener)` â€” callback when a player closes the menu: `(player: Player) -> None`
- `send_to(player: Player)` â€” display the menu to a player. If the player already has a menu open, this menu is queued and shown after the current one closes.
- `close(player: Player) -> bool` â€” close this menu for a player
- `close_all()` â€” close this menu for all players currently viewing it
- `get_viewers() -> list[Player]` â€” list players who currently have this menu open

### MenuTransaction

**Properties:**

- `player` â€” the player who clicked
- `slot` â€” virtual inventory slot index
- `item_clicked` â€” item in the virtual slot before the action
- `item_clicked_with` â€” item in the other slot involved (player inventory or cursor)
- `action_type` â€” the underlying `ItemStackRequestActionType`
- `source` â€” source slot info from the request
- `destination` â€” destination slot info from the request

**Methods:**

- `proceed() -> MenuTransactionResult` â€” allow the transaction to proceed
- `discard() -> MenuTransactionResult` â€” discard transaction

## Usage

```python
from endstone import Player
from endstone.inventory import ItemStack
from endstone_inventoryui import Menu, MenuType, MenuTransaction, MenuTransactionResult

menu = Menu(MenuType.CHEST)

menu.inventory.set_item(0, ItemStack("minecraft:diamond", 1))
menu.inventory.set_item(1, ItemStack("minecraft:emerald", 1))


def on_click(tr: MenuTransaction) -> MenuTransactionResult:
    if tr.slot == 0:
        tr.player.send_message("You clicked the diamond!")
        return tr.discard()
    elif tr.slot == 1:
        tr.player.send_message("You clicked the emerald!")
        return tr.discard()

    return tr.proceed()


menu.set_listener(on_click)
menu.send_to(player)
```

See the [example plugin](./example) for a full project.

## 2.0.7 repair release

InventoryUI now decodes the cereal action discriminator and fixed-width stack IDs used by BDS 1.26.51. Menu opening uses ordered latency acknowledgements, double chests include pairing data, rejected batches receive responses for every request, and close/stop callbacks save while player objects are valid. Item insertion conserves stack counts and rejected drops do not spawn items.

Stop the server before replacing the old wheel. Keep only one version of each plugin in `plugins/`; preserve plugin data folders. InventoryUI-dependent plugins need the InventoryUI wheel in `plugins/`, even when its Python package is already installed.

The legacy shulker material fix first shipped in Backpacks 1.0.92 and is retained in [Backpacks 1.0.93](https://github.com/TheNINJALLO/endstone-ninjos-backpacks/releases/tag/v1.0.93). Use it with InventoryUI 2.0.8. The [live test guide](tests/live/README.md) covers real item interactions as well as menu transactions.
