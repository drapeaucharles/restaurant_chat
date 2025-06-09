# main.py

import uuid
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from schemas.restaurant import RestaurantCreateRequest
from schemas.client import ClientCreateRequest
from schemas.chat import ChatRequest, ChatResponse
from services.restaurant_service import create_restaurant_service
from services.client_service import create_or_update_client_service
from services.chat_service import chat_service
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Create DB tables if not exist
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"]  # <-- allow everything for test

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to open DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Routes ----------------

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}

@app.post("/restaurant/create")
def create_restaurant(req: RestaurantCreateRequest, db: Session = Depends(get_db)):
    result = create_restaurant_service(req, db)
    return result

@app.post("/client/create-or-update")
def create_or_update_client(req: ClientCreateRequest, db: Session = Depends(get_db)):
    result = create_or_update_client_service(req, db)
    return result

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    result = chat_service(req, db)
    return result

@app.post("/chat/logs")
def chat_logs(restaurant_id: str, db: Session = Depends(get_db)):
    logs = db.query(models.ChatLog).filter_by(restaurant_id=restaurant_id).all()
    return [
        {
            "message": log.message,
            "answer": log.answer,
            "client_id": str(log.client_id),
            "table_id": log.table_id,
            "timestamp": log.timestamp
        }
        for log in logs
    ]
