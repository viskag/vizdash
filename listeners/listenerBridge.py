import asyncio
import websockets
import json
import socket
import time

# All connected browser dashboards
dashboard_clients = set()

# All connected Unity instances (usually just one)
unity_clients = set()

# -------------------------------
# WEBSOCKET SERVER (Unity + Browser)
# -------------------------------
async def ws_handler(websocket):
    print("New WS connection")

    try:
        # First message must identify the client
        hello = await websocket.recv()
        hello_data = json.loads(hello)

        if hello_data["type"] == "unity":
            unity_clients.add(websocket)
            print("Unity registered")

        elif hello_data["type"] == "dashboard":
            dashboard_clients.add(websocket)
            print("Dashboard registered")

        # Now handle incoming messages
        async for message in websocket:
            data = json.loads(message)
            
            ####################################################
            print("\n--- UNITY EVENT RECEIVED ---")
            print("Timestamp:", time.time())
            print("Raw Data:", data)
            print("----------------------------\n")

            # If message comes from Unity, forward to dashboards
            if websocket in unity_clients:
                packet = {
                    "type": "unity_event",
                    "timestamp": time.time(),
                    "data": data
                }

                await broadcast_to_dashboards(packet)

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")

    finally:
        unity_clients.discard(websocket)
        dashboard_clients.discard(websocket)


async def broadcast_to_dashboards(packet):
    if not dashboard_clients:
        return

    msg = json.dumps(packet)

    await asyncio.gather(*[
        client.send(msg)
        for client in dashboard_clients
    ], return_exceptions=True)


# -------------------------------
# SHIMMER UDP LISTENER
# -------------------------------
async def shimmer_listener():
    print("Starting UDP listener on 127.0.0.1:9000")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", 9000))
    sock.setblocking(False)

    loop = asyncio.get_running_loop()

    while True:
        data, addr = await loop.sock_recvfrom(sock, 65536)

        decoded = data.decode("utf-8")

        packet = {
            "type": "biosignal",
            "timestamp": time.time(),
            "data": decoded
        }

        await broadcast_to_dashboards(packet)


# -------------------------------
# MAIN ENTRY
# -------------------------------
async def main():
    print("Starting HUB server...")

    ws_server = await websockets.serve(ws_handler, "0.0.0.0", 9100)

    await asyncio.gather(
        shimmer_listener(),
        ws_server.wait_closed()
    )

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
#asyncio.run(main())