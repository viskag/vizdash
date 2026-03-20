# -*- coding: utf-8 -*-
"""
Created on Thu Mar  5 14:36:08 2026

@author: 32474
"""

# -*- coding: utf-8 -*-
"""
Realtime Hub for Shimmer biosignals + Unity events
"""
import asyncio
import websockets
import json
import time

# ----------------------
# Global State
# ----------------------
clients = set()              # all connected dashboard WS clients
hub_start_ts = time.time()   # hub start timestamp in Unix seconds

# ----------------------
# Broadcast helper
# ----------------------
async def broadcast(msg):
    if not clients:
        return
    dead = []
    for c in clients:
        try:
            await c.send(json.dumps(msg))
        except Exception as e:
            print("Removing dead client:", e)
            dead.append(c)
    for d in dead:
        clients.remove(d)

# ----------------------
# WebSocket handler (Unity + Dashboard)
# ----------------------
async def ws_handler(websocket):
    clients.add(websocket)
    print("Client connected")
    try:
        async for message in websocket:
            try:
                evt = json.loads(message)
            except Exception as e:
                print("Failed to parse WS message:", e)
                continue

            # Attach hub-received timestamp
            evt["received_ts"] = time.time()

            # Normalize for dashboard: use t and label
            packet = {
                "type": "unity_event",
                "data": {
                    "t": time.time(),
                    "label": f"{evt.get('actor','')} {evt.get('verb','')} {evt.get('obj','')}".strip()
                }
            }

            print("Received Unity event:", evt)
            print("Broadcasting:", packet)

            await broadcast(packet)

    except websockets.exceptions.ConnectionClosedError as e:
        print("WebSocket connection closed:", e)
    finally:
        clients.remove(websocket)
        print("Client disconnected")

# ----------------------
# Async UDP listener for Shimmer
# ----------------------
class ShimmerProtocol:
    def connection_made(self, transport):
        self.transport = transport
        print("Shimmer UDP listener started on 127.0.0.1:9000")

    def datagram_received(self, data, addr):
        try:
            packet = json.loads(data.decode("utf-8"))
            parsed = parse_shimmer(packet)
            parsed["ts"] = time.time()
            asyncio.create_task(
                broadcast({"type": "biosignal", "data": parsed})
            )
            # Debug log
            # print("Shimmer packet broadcasted:", parsed)
        except Exception as e:
            print("Failed to parse Shimmer packet:", e)

async def shimmer_listener_async():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ShimmerProtocol(),
        local_addr=("127.0.0.1", 9000)
    )

# ----------------------
# Parse Shimmer GSR only
# ----------------------
def parse_shimmer(packet):
    try:
        ts_sec = packet["ts_ms"] / 1000.0
        gsr = None
        hr = None
        for s in packet.get("samples", []):
            if s.get("n") == "GSR Conductance":
                gsr = s.get("v")
            if s.get("n") == "Heart Rate PPG":
                hr = s.get("v")
        return {"ts": time.time(), "gsr": gsr, "hr": hr}
    except Exception as e:
        print("Error parsing Shimmer packet:", e)
        return {"ts": time.time(), "gsr": None, "hr": None}
    
# ----------------------
# Async UDP listener for Tobii Spark gaze
# ----------------------
class TobiiProtocol:
    def connection_made(self, transport):
        self.transport = transport
        print("Tobii UDP listener started on 127.0.0.1:5005")

    def datagram_received(self, data, addr):
        try:
            packet = json.loads(data.decode("utf-8"))
            # Optional: add hub timestamp
            packet["received_ts"] = time.time()
            asyncio.create_task(
                broadcast({"type": "gaze", "data": packet})
            )
            # Debug log
            # print("Tobii packet broadcasted:", packet)
        except Exception as e:
            print("Failed to parse Tobii packet:", e)


async def tobii_listener_async():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: TobiiProtocol(),
        local_addr=("127.0.0.1", 5005)
    )

# ----------------------
# Main
# ----------------------
async def main():
    await shimmer_listener_async()  # start Shimmer UDP listener
    await tobii_listener_async()     # Tobii UDP
    async with websockets.serve(ws_handler, "0.0.0.0", 9100, ping_interval=5):
        print("Realtime Hub running on ws://0.0.0.0:9100")
        await asyncio.Future()  # run forever

# if __name__ == "__main__":
#     asyncio.run(main())
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())