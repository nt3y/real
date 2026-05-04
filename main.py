import subprocess
import sys

# Install dependencies first
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "websockets", "-q"])

import asyncio
import json
import os
import requests
import websockets

TOKEN      = os.environ["DISCORD_TOKEN"]
GUILD_ID   = os.environ["GUILD_ID"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
STATUS     = os.environ.get("STATUS", "online")
SELF_MUTE  = os.environ.get("SELF_MUTE", "true").lower() == "true"
SELF_DEAF  = os.environ.get("SELF_DEAF", "false").lower() == "true"

API = "https://discord.com/api/v10"

res = requests.get(f"{API}/users/@me", headers={"Authorization": TOKEN})
if res.status_code != 200:
    print(f"[ERROR] Invalid token! Status: {res.status_code}")
    sys.exit(1)

user = res.json()
print(f"[OK] Logged in as {user['username']} ({user['id']})")

async def heartbeat(ws, interval):
    while True:
        await asyncio.sleep(interval / 1000)
        await ws.send(json.dumps({"op": 1, "d": None}))

async def main():
    print("[INFO] Connecting to Discord gateway...")
    async with websockets.connect("wss://gateway.discord.gg/?v=10&encoding=json", max_size=10*1024*1024) as ws:
        hello = json.loads(await ws.recv())
        interval = hello["d"]["heartbeat_interval"]
        asyncio.create_task(heartbeat(ws, interval))

        await ws.send(json.dumps({
            "op": 2,
            "d": {
                "token": TOKEN,
                "properties": {"$os": "linux", "$browser": "chrome", "$device": "pc"},
                "presence": {"status": STATUS, "afk": False}
            }
        }))

        while True:
            event = json.loads(await ws.recv())
            if event.get("op") == 9:
                print("[ERROR] Invalid session. Check your token.")
                sys.exit(1)
            if event.get("t") == "READY":
                print("[OK] Gateway READY!")
                break

        print(f"[INFO] Joining voice channel {CHANNEL_ID}...")
        await ws.send(json.dumps({
            "op": 4,
            "d": {
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "self_mute": SELF_MUTE,
                "self_deaf": SELF_DEAF
            }
        }))
        print("[OK] Joined voice channel!")

        while True:
            try:
                event = json.loads(await ws.recv())
                if event.get("t"):
                    print(f"[EVENT] {event.get('t')}")
            except websockets.exceptions.ConnectionClosed:
                print("[WARN] Disconnected. Reconnecting...")
                break

async def run():
    while True:
        try:
            await main()
        except SystemExit:
            raise
        except Exception as e:
            print(f"[ERROR] {e} — retrying in 5s...")
            await asyncio.sleep(5)

asyncio.run(run())
