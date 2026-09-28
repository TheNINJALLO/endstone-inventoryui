"""Real BDS / InventoryUI / Backpacks acceptance test in a disposable directory."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, sys, threading, time, tomllib
from zipfile import ZipFile
from endstone.cli.windows import WindowsBootstrap, PopenWithDll
p=argparse.ArgumentParser()
p.add_argument("--workspace",type=Path,required=True)
p.add_argument("--run",required=True)
p.add_argument("--vault",action="store_true")
p.add_argument("--wheel-dir",type=Path)
p.add_argument("--interaction",choices=("air","block"))
p.add_argument("--tier",choices=("small","large","gigantic"),default="gigantic")
p.add_argument("--legacy-material",action="store_true")
a=p.parse_args(); ws=a.workspace.resolve(); root=ws/"endstone-inventoryui-main"; out=root/"scratch"/a.run
out.mkdir(exist_ok=False); server=out/"server"; server.mkdir(); probe=out/"python"; probe.mkdir()
source=ws/"endstone-paradox/scratch/servers/windows"
for entry in source.iterdir():
    if entry.name in {"worlds","plugins","logs",".sentry-native","server.properties","endstone.toml","permissions.json","allowlist.json"}:continue
    target=server/entry.name
    if entry.is_dir():
        subprocess.run(["powershell","-NoProfile","-Command", "New-Item -ItemType Junction -Path $env:REPAIR_LINK -Target $env:REPAIR_TARGET | Out-Null"],env=dict(os.environ,REPAIR_LINK=str(target),REPAIR_TARGET=str(entry)),check=True)
    else:os.link(entry,target)
(server/"plugins").mkdir()
(server/"server.properties").write_text("server-name=Paradox acceptance test\nlevel-name=paradox-acceptance\nserver-port=39431\nserver-portv6=39432\nonline-mode=false\nallow-cheats=true\ngamemode=survival\ndifficulty=peaceful\nlevel-type=FLAT\nview-distance=4\ntick-distance=4\nemit-server-telemetry=false\ntransport=nethernet\n")
(server/"endstone.toml").write_text("[settings]\n")
for name,source in [("endstone_inventoryui",root/"src/endstone_inventoryui"),("ninjos_backpacks",ws/"endstone-backpacks/src/ninjos_backpacks"),("endstone_inventory_manager",ws/"endstone-inventory-manager/src/endstone_inventory_manager")]:
    if not a.wheel_dir: shutil.copytree(source,probe/name,ignore=shutil.ignore_patterns("__pycache__"))
if a.wheel_dir:
    for wheel in a.wheel_dir.glob("*.whl"):
        with ZipFile(wheel) as z: z.extractall(probe)
for name in ("bedrock_protocol","rapidnbt","pymysql","bstream"):
    source=ws/"endstone-schematic-cloud/.venv/Lib/site-packages"/name
    if not source.exists(): source=Path(sys.base_prefix)/"Lib/site-packages"/name
    shutil.copytree(source,probe/name,ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy2(root/"tests/live/probe.py",probe/"repair_probe.py")
for name,repository,entry in [("endstone_inventoryui",root,"inventoryui = endstone_inventoryui:InventoryUIPlugin"),("endstone_ninjos_backpacks",ws/"endstone-backpacks","ninjos_backpacks = ninjos_backpacks.plugin:NinjOSBackpacks"),("endstone_inventory_manager",ws/"endstone-inventory-manager","inventory-manager = endstone_inventory_manager:InventoryManagerPlugin"),("endstone_repair_probe",None,"repair-probe = repair_probe:Probe")]:
    if a.wheel_dir and name != "endstone_repair_probe": continue
    version=tomllib.loads((repository/"pyproject.toml").read_text(encoding="utf-8"))["project"]["version"] if repository else "1.0.0"
    dist=probe/f"{name}-{version}.dist-info";dist.mkdir()
    (dist/"METADATA").write_text(f"Metadata-Version: 2.1\nName: {name.replace('_','-')}\nVersion: {version}\n")
    (dist/"entry_points.txt").write_text("[endstone]\n"+entry+"\n")
(probe/"sitecustomize.py").write_text('import os,sys\nsys.path[:]=[p for p in sys.path if "site-packages" not in p.lower() or p.lower().startswith(os.environ["REPAIR_PREFIX"].lower())]\n')
(out/"control.json").write_text('{"id":0,"action":"wait"}')
boot=WindowsBootstrap(str(server),True,"",False);env=boot._endstone_runtime_env.copy();env.update(PYTHONPATH=str(probe)+os.pathsep+env["PYTHONPATH"],REPAIR_PREFIX=sys.prefix,REPAIR_VAULT="1" if a.vault else "0",REPAIR_INTERACTION=a.interaction or "",REPAIR_TIER=a.tier,REPAIR_LEGACY_MATERIAL="1" if a.legacy_material else "0",INVENTORY_PROBE_OUTPUT=str(out),PYTHONNOUSERSITE="1")
process=PopenWithDll([str(boot.executable_path)],cwd=server,env=env,dll_names=str(boot._endstone_runtime_path),creationflags=subprocess.CREATE_NO_WINDOW,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
lines=[]
def read():
    for line in process.stdout:
        lines.append(line)
        with (out/"server.log").open("a",encoding="utf-8") as log:log.write(line)
threading.Thread(target=read,daemon=True).start();client=None;events=[];report={"checks":[],"interaction":a.interaction,"tier":a.tier,"legacy_material":a.legacy_material,"wheel_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.wheel_dir.glob("*.whl")} if a.wheel_dir else {}}
def snapshot():
    try:return json.loads((out/"snapshot.json").read_text())
    except (FileNotFoundError,json.JSONDecodeError):return {}
def wait(predicate,label,timeout=45):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if (out/"error.txt").exists():raise AssertionError((out/"error.txt").read_text())
        if predicate():return
        if process.poll() is not None:break
        time.sleep(.1)
    raise AssertionError(f"Timed out: {label}; snapshot={snapshot()}; server={''.join(lines[-20:])}")
def send(action,**kw):
    client.stdin.write(json.dumps(dict(name="InventoryTest",action=action,**kw))+"\n");client.stdin.flush()
def transfer(request,source,slot,dest,target,count,stack=0):
    send("transfer",request_id=request,Count=count,Source={"Container":{"ContainerID":source},"Slot":slot,"StackNetworkID":stack},Destination={"Container":{"ContainerID":dest},"Slot":target,"StackNetworkID":0})
    wait(lambda:any(e.get("event")=="stack_response" and any(r["RequestID"]==request for r in e["value"]["Responses"]) for e in events),f"response {request}")
try:
    wait(lambda:any("Server started" in l for l in lines),"server startup",120)
    client=subprocess.Popen([str(root/"scratch/client/bedrock-inventory-client.exe"),"-transport","lan","-address","127.0.0.1:39431","-names","InventoryTest","-duration","180s"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",creationflags=subprocess.CREATE_NO_WINDOW)
    def read_client():
        with (out/"client.log").open("w",encoding="utf-8") as log:
            for line in client.stdout:
                log.write(line);log.flush()
                try:events.append(json.loads(line))
                except json.JSONDecodeError:pass
    threading.Thread(target=read_client,daemon=True).start()
    wait(lambda:"player" in snapshot(),"player join")
    wait(lambda:abs(snapshot().get("location",[0,32768,0])[1])<320,"player spawned in the world")
    (out/"control.json").write_text('{"id":1,"action":"seed"}')
    if a.interaction:
        wait(lambda:snapshot().get("id")==1,"physical backpack assigned")
        wait(lambda:any(e.get("event")=="inventory_content" and e["value"].get("WindowID")==0 and len(e["value"].get("Content",[]))>8 and e["value"]["Content"][8]["Stack"]["Count"]==1 for e in events),"client received backpack")
        send("hotbar",slot=8)
        wait(lambda:snapshot().get("held_slot")==8,"backpack selected")
        send("use_"+a.interaction,slot=8,block_position=snapshot()["target"],block_runtime_id=snapshot()["target_runtime_id"])
    wait(lambda:snapshot().get("state")=="OPEN","open acknowledged")
    wait(lambda:any(e.get("event")=="inventory_content" and e["value"].get("WindowID")==2 for e in events),"client decoded contents")
    if a.interaction:
        assert any(i["action"]=="RIGHT_CLICK_"+a.interaction.upper() and i["cancelled"] and i["item_id"]=="InventoryTest" for i in snapshot()["interactions"]), snapshot()
        report["checks"].append("assigned backpack opens through real " + a.interaction + " interaction")
    report["checks"].append("chest menu open acknowledged and contents decoded")
    if a.vault:
        def total_player(): return sum(i["amount"] for i in snapshot()["player"] if i and i["type"]=="minecraft:diamond")
        transfer(-1,12,0,7,0,5)
        wait(lambda:snapshot()["cache"]["0"]["amount"]==105,"virtual merge")
        assert total_player()==7
        transfer(-3,7,0,12,1,1,snapshot()["stack_ids"]["0"])
        wait(lambda:snapshot()["cache"]["0"]["amount"]==41,"virtual withdrawal")
        assert total_player()==71, snapshot()
        transfer(-5,7,53,59,0,1,snapshot()["stack_ids"]["53"])
        wait(lambda:snapshot().get("page")==1,"virtual next page")
        transfer(-7,7,45,59,0,1,snapshot()["stack_ids"]["45"])
        wait(lambda:snapshot().get("page")==0,"virtual previous page")
        assert snapshot()["cache"]["0"]["amount"]==41
        donor = next(i for i,item in enumerate(snapshot()["player"]) if item and item["amount"] >= 3)
        transfer(-9,12,donor,59,0,3)
        transfer(-11,59,0,7,0,2)
        wait(lambda:snapshot()["cache"]["0"]["amount"]==43,"cursor deposit")
        transfer(-13,59,0,12,35,1)
        wait(lambda:snapshot()["player"][35] is not None,"cursor remainder")
        assert total_player()==69, snapshot()
        assert snapshot()["player"][35]["marker"]=="preserve custom NBT"
        report["checks"].append("cursor partial deposit preserves remainder and custom NBT")
        report["checks"].append("virtual vault merge, withdrawal, and both page buttons conserve 112 items")
    else:
        transfer(-1,12,0,7,0,5)
        wait(lambda:snapshot()["menu"][0] is not None and snapshot()["menu"][0]["amount"]==5,"deposit")
        assert snapshot()["player"][0]["amount"]==7
        transfer(-3,7,0,12,1,2,snapshot()["stack_ids"]["0"])
        wait(lambda:snapshot()["menu"][0]["amount"]==3,"withdraw")
        assert snapshot()["player"][1]["amount"]==2
        assert snapshot()["player"][1]["name"]=="Inventory repair test"
        assert snapshot()["player"][1]["marker"]=="preserve custom NBT"
        report["checks"].append("deposit and withdraw conserve named items")
        if a.tier == "gigantic":
            transfer(-5,7,53,59,0,1,snapshot()["stack_ids"]["53"])
            wait(lambda:snapshot().get("page")==1,"next page")
            transfer(-7,7,45,59,0,1,snapshot()["stack_ids"]["45"])
            wait(lambda:snapshot().get("page")==0,"previous page")
            assert snapshot()["menu"][0]["amount"]==3
            report["checks"].append("next and previous page actions preserve contents")
        send("menu_close")
        wait(lambda:snapshot().get("state")==None,"close")
        assert snapshot()["saved"]["contents"]["0"]["amount"]==3
        (out/"control.json").write_text('{"id":2,"action":"open"}')
        if a.interaction:
            send("use_"+a.interaction,slot=8,block_position=snapshot()["target"],block_runtime_id=snapshot()["target_runtime_id"])
        wait(lambda:snapshot().get("state")=="OPEN","reopen")
        assert snapshot()["menu"][0]["amount"]==3
        assert snapshot()["menu"][0]["name"]=="Inventory repair test"
        assert snapshot()["menu"][0]["marker"]=="preserve custom NBT"
        report["checks"].append("SQLite close and reopen preserve contents and metadata")
        transfer(-9,12,0,7,0,1)
        wait(lambda:snapshot()["menu"][0]["amount"]==4,"last move before stop")

finally:
    if process.poll() is None:
        process.stdin.write("stop\n");process.stdin.flush()
        try:process.wait(timeout=35)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    if client and client.poll() is None:client.terminate();client.wait(timeout=10)
    (out/"server.log").write_text("".join(lines),encoding="utf-8")
    report["server_exit"]=process.returncode
    (out/"results.json").write_text(json.dumps(report,indent=2))
assert process.returncode==0, process.returncode
with sqlite3.connect(server/"plugins/ninjos_backpacks/backpacks.db") as db:
    contents=json.loads(db.execute("SELECT contents FROM item_backpacks WHERE backpack_id=?",("block:Overworld:0:-60:0" if a.vault else ("InventoryTest" if a.interaction else "repair-fixture")+"_"+a.tier,)).fetchone()[0])
    assert contents["0"]["amount"]==(43 if a.vault else 4), contents
report["checks"].append("stop with an open backpack flushes SQLite without a crash")
assert not any("PacketViolationWarning" in l or "[Backpack ERROR]" in l for l in lines), "Server reported a packet or interaction error"
assert not any(e.get("event")=="packet_violation" for e in events), "Client received a packet violation warning"
report["passed"]=True
(out/"results.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
