import asyncio
import websockets
import json
import socket
import threading
import time

# All connected dashboard clients
clients = set()
hub_start_ts = time.time()  # record hub start in Unix seconds
###########################################
# -------- WEBSOCKET SERVER (Unity + Web) -
###########################################

# async def ws_handler(websocket):
#     clients.add(websocket)
#     print("Client connected")

#     try:
#         async for message in websocket:
#             # Message coming FROM Unity
#             evt = json.loads(message)

#             evt["received_ts"] = time.time()

#             await broadcast({
#                 "type": "unity_event",
#                 "data": evt
#             })

#     finally:
#         clients.remove(websocket)
#         print("Client disconnected")
async def ws_handler(websocket):
    clients.add(websocket)
    print("Client connected")

    try:
        async for message in websocket:
            evt = json.loads(message)

        # Make a simple structure for plotting
        packet = {
            "type": "unity_event",
            "data": {
                "t": hub_start_ts + evt.get("timestamp", 0),  # numeric x-axis
                "label": f"{evt.get('actor','')} {evt.get('verb','')} {evt.get('obj','')}".strip()
                }
            }
        print("Received Unity event:", evt)# <- raw data from Unity
        print("Broadcasting to dashboards:", packet)# <- normalized packet

        await broadcast(packet)

    finally:
        clients.remove(websocket)
        print("Client disconnected")

###########################################
# -------- BROADCAST FUNCTION -------------
###########################################

async def broadcast(msg):
    if not clients:
        return

    dead = []
    for c in clients:
        try:
            await c.send(json.dumps(msg))
        except:
            dead.append(c)

    for d in dead:
        clients.remove(d)

###########################################
# -------- SHIMMER UDP LISTENER -----------
###########################################

# def shimmer_listener(loop):
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.bind(("127.0.0.1", 9000))
#     print("Listening Shimmer on 9000")

#     while True:
#         data, _ = sock.recvfrom(65536)
#         msg = json.loads(data.decode("utf-8"))

#         parsed = parse_shimmer(msg)

#         asyncio.run_coroutine_threadsafe(
#             broadcast({
#                 "type": "biosignal",
#                 "data": parsed
#             }),
#             loop
#         )
def shimmer_listener(loop):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 9000))
    print("Listening Shimmer on 9000")

    while True:
        data, _ = sock.recvfrom(65536)
        msg = json.loads(data.decode("utf-8"))

        # Convert Shimmer ts_ms to current Unix time (approx)
        parsed = parse_shimmer(msg)
        parsed["ts"] = hub_start_ts + parsed["ts"]  # align to hub start

        asyncio.run_coroutine_threadsafe(
            broadcast({
                "type": "biosignal",
                "data": parsed
            }),
            loop
        )

###########################################
# -------- PARSE ONLY WHAT WE NEED --------
###########################################

# def parse_shimmer(packet):
#     ts = packet["ts_ms"]

#     gsr = None

#     for s in packet["samples"]:
#         if s["n"] == "GSR Conductance":
#             gsr = s["v"]

#     return {
#         "ts": ts,
#         "gsr": gsr
#     }
def parse_shimmer(packet):
    # ts_ms from Shimmer in milliseconds
    ts_sec = hub_start_ts + packet["ts_ms"]/1000.0  # convert to Unix seconds
    gsr = None
    for s in packet["samples"]:
        if s["n"] == "GSR Conductance":
            gsr = s["v"]
    return {"ts": ts_sec, "gsr": gsr}

###########################################
# -------- MAIN ---------------------------
###########################################

async def main():
    loop = asyncio.get_running_loop()

    threading.Thread(target=shimmer_listener, args=(loop,), daemon=True).start()

    async with websockets.serve(ws_handler, "0.0.0.0", 9100):
        print("Realtime Hub running on :9100")
        await asyncio.Future()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())






















# # -*- coding: utf-8 -*-
# import asyncio
# import websockets
# import json
# import socket
# import time

# clients = set()

# ###########################################
# # -------- BROADCAST ----------------------
# ###########################################

# async def broadcast(msg):
#     if not clients:
#         return

#     dead = []
#     for c in clients:
#         try:
#             await c.send(json.dumps(msg))
#         except:
#             dead.append(c)

#     for d in dead:
#         clients.discard(d)

# ###########################################
# # -------- UNITY / DASHBOARD WS -----------
# ###########################################

# async def ws_handler(websocket):
#     clients.add(websocket)
#     print("Client connected")

#     try:
#         async for message in websocket:
#             evt = json.loads(message)

#             # Stamp with HUB TIME (critical!)
#             packet = {
#                 "type": "unity_event",
#                 "t": time.perf_counter(),
#                 "label": evt
#             }

#             await broadcast(packet)

#     except websockets.exceptions.ConnectionClosed:
#         pass

#     finally:
#         clients.discard(websocket)
#         print("Client disconnected")

# ###########################################
# # -------- SHIMMER UDP LISTENER -----------
# ###########################################

# async def shimmer_listener():
#     print("UDP listener started on 127.0.0.1:9000")

#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.bind(("127.0.0.1", 9000))
#     sock.setblocking(False)

#     loop = asyncio.get_running_loop()

#     while True:
#         data, _ = await loop.sock_recvfrom(sock, 65536)

#         decoded = json.loads(data.decode("utf-8"))

#         gsr = None
#         for s in decoded["samples"]:
#             if s["n"] == "GSR Conductance":
#                 gsr = s["v"]
#                 break

#         if gsr is None:
#             continue

#         packet = {
#             "type": "biosignal",
#             "t": time.perf_counter(),  # SAME CLOCK AS UNITY
#             "gsr": gsr
#         }

#         await broadcast(packet)

# ###########################################
# # -------- MAIN ---------------------------
# ###########################################

# async def main():
#     print("Starting Realtime Hub on :9100")

#     ws_server = await websockets.serve(
#         ws_handler,
#         "0.0.0.0",
#         9100,
#         ping_interval=20,
#         ping_timeout=20
#     )

#     await asyncio.gather(
#         shimmer_listener(),
#         ws_server.wait_closed()
#     )

# try:
#     loop = asyncio.get_running_loop()
# except RuntimeError:
#     loop = None

# if loop and loop.is_running():
#     # Running inside Spyder/IPython
#     print("Detected Spyder/IPython event loop — scheduling task...")
#     loop.create_task(main())
# else:
#     # Normal Python execution
#     asyncio.run(main())
