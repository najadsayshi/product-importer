import redis.asyncio as redis

async def import_websocket(websocket, task_id):
    await websocket.accept()

    r = redis.from_url(
        os.getenv("REDIS_URL"),
        decode_responses=True
    )
    pubsub = r.pubsub()
    await pubsub.subscribe(task_id)

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5)
            if msg:
                await websocket.send_text(msg["data"])
                if msg["data"] == "done":
                    break

    except:
        pass
    finally:
        await websocket.close()
