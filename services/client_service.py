# services/client_service.py

from sqlalchemy.orm import Session
import models
from pinecone_utils import insert_client_preferences
from schemas.client import ClientCreateRequest

def create_or_update_client_service(req: ClientCreateRequest, db: Session):
    client = db.query(models.Client).filter_by(id=req.client_id).first()

    if client:
        client.preferences = req.preferences
    else:
        client = models.Client(
            id=req.client_id,
            preferences=req.preferences,
            restaurants_visited=[]
        )
        db.add(client)

    db.commit()

    # Inject client preferences into Pinecone
    insert_client_preferences(req.client_id, req.preferences)

    return {"status": "client_updated"}
