import os, uuid
from fastapi import FastAPI, UploadFile, File, Depends, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import tasks, ws, crud
from .models import Base
from sqlalchemy import create_engine
from .db import DATABASE_URL

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
            chunk = await file.read(1024*1024)
            if not chunk:
                break
            f.write(chunk)
    result = tasks.import_csv_task.delay(path)
    return {"task_id": result.id, "status": "queued"}

@app.websocket("/ws/import/{task_id}")
async def import_ws(websocket: WebSocket, task_id: str):
    await ws.import_websocket(websocket, task_id)

@app.get("/api/products")
def list_products(page: int = 1, per_page: int = 50, sku: str = None, name: str = None, active: bool = None, db: Session = Depends(get_db)):
    skip = (page - 1) * per_page
    items = crud.get_products(db, skip=skip, limit=per_page, sku=sku, name=name, active=active)
    return {"items": [dict(id=i.id, sku=i.sku, name=i.name, description=i.description, price=str(i.price), active=i.active) for i in items]}

@app.post("/api/products")
def create_product(sku: str, name: str = None, description: str = None, price: float = 0.0, active: bool = True, db: Session = Depends(get_db)):
    row = crud.create_or_update_product(db, sku=sku, name=name, description=description, price=price, active=active)
    return {"product": dict(row)}

@app.post("/api/products/delete_all")
def delete_all(confirm: bool = False, db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Must pass confirm=true")
    crud.delete_all_products(db)
    return {"status":"ok"}
