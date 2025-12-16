import asyncio
import websockets
import json

JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY1OTU1MTUzLCJpYXQiOjE3NjU4Njg3NTMsImp0aSI6IjE5ZTM2ZWJmYmQzMDQ5NGE4NmU1MDZlZDRjMDhiZTg0IiwidXNlcl9pZCI6IjEifQ.4jucAImtW9cLcGfBvmCOCxxdW0WqSsX0T75KdFlEuAE"
conversation_slug = "shishir-gautam-1"

async def test_chat():
    uri = f"ws://localhost:8000/ws/chat/{conversation_slug}/?token={JWT_TOKEN}"

    async with websockets.connect(uri) as ws:
        print("success")
asyncio.run(test_chat())
