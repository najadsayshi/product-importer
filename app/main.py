import os, uuid
from fastapi import FastAPI, UploadFile, File, WebSocket, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import crud, tasks, ws

UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    task_id = uuid.uuid4().hex
    tasks.start_import(path, task_id)

    return {"task_id": task_id}

@app.websocket("/ws/import/{task_id}")
async def import_ws(websocket: WebSocket, task_id: str):
    await ws.import_websocket(websocket, task_id)

@app.get("/api/products")
def list_products(page: int = 1, per_page: int = 50, db: Session = Depends(get_db)):
    skip = (page - 1) * per_page
    items = crud.get_products(db, skip=skip, limit=per_page)
    return {"items": [dict(
        id=i.id, sku=i.sku, name=i.name, description=i.description,
        price=str(i.price), active=i.active
    ) for i in items]}
