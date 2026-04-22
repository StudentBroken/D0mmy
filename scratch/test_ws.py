import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://127.0.0.1:8000/ws/ide/test-client"
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to D0mmy backend!")
            # Send a ping
            await websocket.send(json.dumps({"type": "ping", "payload": {}}))
            # Wait for response
            response = await websocket.recv()
            print(f"Received from backend: {response}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
