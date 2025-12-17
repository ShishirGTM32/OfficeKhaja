import asyncio
import websockets
import json

async def test_chat():
    conversation_slug = "shishir-gautam-1"
    JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2MDMzMjQxLCJpYXQiOjE3NjU5NDY4NDEsImp0aSI6ImFhMDQ5M2EwNzQzZTQ4NjdiMjM1NTlhOWU3YjZiNjYyIiwidXNlcl9pZCI6IjEyIn0.NmiIqpBk7OBsS07rE8-ajcoi3SH2UcY1gtYlBT4WS84"
    uri = f"ws://localhost:8000/ws/chat/{conversation_slug}/?token={JWT_TOKEN}"
    async with websockets.connect(uri) as ws:
        message_data = {"type": "read"}
        await ws.send(json.dumps(message_data))

        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("No response received within 5 seconds")
        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed unexpectedly")
asyncio.run(test_chat())
