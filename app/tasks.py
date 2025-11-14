import csv, time
import threading
import redis.asyncio as redis

from .crud import create_or_update_product
from .db import SessionLocal

r = redis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True
)

def process_csv(path, task_id):
    db = SessionLocal()
    try:
        with open(path, newline='') as f:
            reader = list(csv.reader(f))
            total = len(reader)

            for i, row in enumerate(reader):
                if i == 0:
                    continue  # header

                sku, name, desc, price, active = row
                create_or_update_product(
                    db, sku=sku, name=name, description=desc,
                    price=float(price), active=(active.lower() == "true")
                )

                progress = int((i / total) * 100)
                r.publish(task_id, str(progress))
                time.sleep(0.05)

        r.publish(task_id, "done")

    except Exception as e:
        r.publish(task_id, f"error:{str(e)}")

    finally:
        db.close()

def start_import(path, task_id):
    thread = threading.Thread(target=process_csv, args=(path, task_id))
    thread.start()
