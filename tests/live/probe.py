from pathlib import Path
import json, math, os, traceback
from endstone.plugin import Plugin
from endstone.inventory import ItemStack
from endstone.event import event_handler, EventPriority, PlayerInteractEvent
from endstone_inventoryui.manager.player_manager import find_session
class Probe(Plugin):
    api_version = "0.11"
    depend = ["inventoryui", "ninjos_backpacks", "inventory_manager"]
    def on_enable(self):
        self.root = Path(os.environ["INVENTORY_PROBE_OUTPUT"])
        self.last = 0
        self.interactions = []
        self.register_events(self)
        self.server.scheduler.run_task(self, self.tick, delay=20, period=2)
    @event_handler(priority=EventPriority.MONITOR)
    def on_interact(self, event: PlayerInteractEvent):
        from ninjos_backpacks.serializer import get_backpack_id_from_item
        self.interactions.append({"action":event.action.name,"cancelled":event.is_cancelled,
                                  "item_id":get_backpack_id_from_item(event.item)})
    def tick(self):
        try:
            players = list(self.server.online_players)
            if not players: return
            player = players[0]
            bp = self.server.plugin_manager.get_plugin("ninjos_backpacks")
            vault = os.environ.get("REPAIR_VAULT") == "1"
            interaction = os.environ.get("REPAIR_INTERACTION", "")
            tier = os.environ.get("REPAIR_TIER", "gigantic")
            key = "block:"+player.dimension.name+":0:-60:0" if vault else (player.name if interaction else "repair-fixture")+"_"+tier
            command = json.loads((self.root / "control.json").read_text())
            if command["id"] != self.last:
                self.last = command["id"]
                if command["action"] == "seed":
                    player.inventory.clear()
                    item = ItemStack("minecraft:diamond", 12)
                    meta = item.item_meta
                    meta.display_name = "Inventory repair test"
                    meta.lore = ["Must survive transfer and reopen"]
                    item.set_item_meta(meta)
                    from endstone.nbt import StringTag
                    tag = item.nbt
                    tag["repair_marker"] = StringTag("preserve custom NBT")
                    item.nbt = tag
                    player.inventory.set_item(0, item)
                    if vault:
                        from endstone.level import Location
                        if command["action"] == "seed":
                            from ninjos_backpacks.serializer import serialize_item
                            stored = serialize_item(item)
                            stored["amount"] = 100
                            bp.db.save_item_backpack(key,"vault_gigantic",90,str(player.unique_id),player.name,{"0":stored})
                        bp.manager.open_block_storage(player,Location(player.dimension,0,-60,0),"vault_gigantic")
                    elif interaction:
                        if os.environ.get("REPAIR_LEGACY_MATERIAL") == "1":
                            bp.cfg.item_backpacks["gigantic"]["material"] = "minecraft:shulker_box"
                        bp.cmd_handler.give_backpack(self.server.command_sender,player,tier,None,None)
                        player.inventory.set_item(8,player.inventory.get_item(1))
                        player.inventory.set_item(1,None)
                        # Seed the protocol client's inventory explicitly; it has
                        # no retail inventory-screen controller to request a refresh.
                        from endstone_inventoryui.network.inventory_content_packet import InventoryContentPacket
                        from endstone_inventoryui.network.item_stack_wrapper import ItemStackWrapper
                        packet=InventoryContentPacket(0)
                        packet.items=[ItemStackWrapper(0,player.inventory.get_item(i)) for i in range(36)]
                        player.send_packet(packet.get_packet_id(),packet.serialize())
                        pos=player.location
                        self.target=[math.floor(pos.x)+1,math.floor(pos.y),math.floor(pos.z)]
                        self.server.dispatch_command(self.server.command_sender,"setblock "+" ".join(map(str,self.target))+" stone")
                    else:
                        bp.manager.open_item_backpack(player, "repair-fixture", tier)
                elif command["action"] == "open":
                    if vault:
                        from endstone.level import Location
                        if command["action"] == "seed":
                            from ninjos_backpacks.serializer import serialize_item
                            stored = serialize_item(item)
                            stored["amount"] = 100
                            bp.db.save_item_backpack(key,"vault_gigantic",90,str(player.unique_id),player.name,{"0":stored})
                        bp.manager.open_block_storage(player,Location(player.dimension,0,-60,0),"vault_gigantic")
                    elif not interaction:
                        bp.manager.open_item_backpack(player, "repair-fixture", tier)
            def describe(item):
                if item is None or item.type.id == "minecraft:air": return None
                return {"type": item.type.id, "amount": item.amount, "name": item.item_meta.display_name, "marker": item.nbt["repair_marker"].value if "repair_marker" in item.nbt else None}
            session = find_session(player)
            result = {"id":self.last, "player":[describe(player.inventory.get_item(i)) for i in range(36)],
                      "cache":bp.manager.contents_caches.get(str(player.unique_id)),
                      "page":bp.manager.active_pages.get(str(player.unique_id)),
                      "saved":bp.db.get_item_backpack(key),
                      "interactions":self.interactions,"held_slot":player.inventory.held_item_slot,
                      "location":[player.location.x,player.location.y,player.location.z],
                      "target":getattr(self,"target",None),
                      "target_runtime_id":self.server.create_block_data("minecraft:stone").runtime_id,
                      "state":session.state.name if session else None,
                      "menu":[describe(i) for i in session.menu.inventory.contents] if session else []}
            if session:
                result["stack_ids"] = {str(i):session.container_manager.tracker.get_stack_id(7,i) for i in range(54)}
            (self.root / "snapshot.json").write_text(json.dumps(result))
        except Exception:
            (self.root / "error.txt").write_text(traceback.format_exc())
