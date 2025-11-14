from fastapi import WebSocket, WebSocketDisconnect
import aioredis
import os
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

async def import_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    redis = await aioredis.create_redis(REDIS_URL)
    try:
        res = await redis.subscribe(f"import:{task_id}")
        ch = res[0]
        while await ch.wait_message():
            msg = await ch.get(encoding="utf-8")
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
    finally:
        redis.close()
        await redis.wait_closed()
