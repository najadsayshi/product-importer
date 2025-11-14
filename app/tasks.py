import os, uuid, json
from celery import Celery
import redis
import psycopg2
from psycopg2 import sql

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/1"))
PG_DSN = os.getenv("PG_DSN") or os.getenv("DATABASE_URL").replace("postgresql+psycopg2://", "host=")  # not ideal locally; we'll use DATABASE_URL in render
REDIS_CHANNEL_PREFIX = "import:"

celery = Celery("worker", broker=CELERY_BROKER, backend=CELERY_BACKEND)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", CELERY_BROKER))

def publish_progress(task_id, payload):
    try:
        redis_client.publish(REDIS_CHANNEL_PREFIX + task_id, json.dumps(payload))
    except Exception:
        pass

@celery.task(bind=True)
def import_csv_task(self, file_path):
    task_id = self.request.id
    publish_progress(task_id, {"phase":"START", "progress":0, "message":"Starting import"})
    # Use DATABASE_URL directly via psycopg2 connect
    db_url = os.getenv("DATABASE_URL")
    if db_url is None:
        publish_progress(task_id, {"phase":"ERROR", "progress":0, "message":"DATABASE_URL missing"})
        raise RuntimeError("DATABASE_URL not set")

    # Convert SQLAlchemy DB URL to psycopg2 dsn for simple usage
    # Example DATABASE_URL: postgresql+psycopg2://user:pass@host:5432/dbname
    dsn = db_url.replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    staging = f"staging_{uuid.uuid4().hex[:8]}"
    try:
        cur.execute(sql.SQL("CREATE TEMP TABLE {} (sku text, name text, description text, price numeric, active boolean DEFAULT true) ON COMMIT DROP;").format(sql.Identifier(staging)))
        conn.commit()
        publish_progress(task_id, {"phase":"PARSING", "progress":10, "message":"Copying CSV into staging"})
        with open(file_path, "r", encoding="utf-8") as f:
            cur.copy_expert(sql.SQL("COPY {} (sku, name, description, price, active) FROM STDIN WITH CSV HEADER").format(sql.Identifier(staging)), f)
            conn.commit()
        publish_progress(task_id, {"phase":"COPIED", "progress":60, "message":"Applying upsert from staging"})
        upsert_sql = sql.SQL("""
            INSERT INTO products (sku, name, description, price, active, created_at, updated_at)
            SELECT sku, name, description, price, active, now(), now() FROM {}
            ON CONFLICT ON CONSTRAINT products_sku_lower_idx
            DO UPDATE SET
              name = EXCLUDED.name,
              description = EXCLUDED.description,
              price = EXCLUDED.price,
              active = EXCLUDED.active,
              updated_at = now();
        """).format(sql.Identifier(staging))
        cur.execute(upsert_sql)
        conn.commit()
        publish_progress(task_id, {"phase":"DONE", "progress":100, "message":"Import complete"})
    except Exception as e:
        conn.rollback()
        publish_progress(task_id, {"phase":"ERROR", "progress":0, "message": str(e)})
        raise
    finally:
        cur.close()
        conn.close()
        try:
            os.remove(file_path)
        except Exception:
            pass
    return {"status":"ok"}
