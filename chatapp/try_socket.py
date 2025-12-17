import asyncio
import websockets
import json

JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY1OTY5NTA5LCJpYXQiOjE3NjU4ODMxMDksImp0aSI6ImM3ZGVhMGU2MmY3ZTRjZGFhMzY2ZDE2MTVkMjBkOWI5IiwidXNlcl9pZCI6IjEyIn0.RZwHnF2w-u1SYKeu3BSdUkiD8QT89-Oyw4STEN-Zmb4"
conversation_slug = "shishir-gautam-1"

async def test_chat():
    uri = f"ws://localhost:8000/ws/chat/{conversation_slug}/?token={JWT_TOKEN}"

    async with websockets.connect(uri) as ws:
        print("success")
asyncio.run(test_chat())
