# services/restaurant_service.py

from sqlalchemy.orm import Session
import models
from pinecone_utils import insert_restaurant_data
from schemas.restaurant import RestaurantCreateRequest

def create_restaurant_service(req: RestaurantCreateRequest, db: Session):
    # Insert into DB
    restaurant = models.Restaurant(
        restaurant_id=req.restaurant_id,
        data=req.data.dict()
    )
    db.add(restaurant)
    db.commit()

    # Inject into Pinecone
    insert_restaurant_data(req.restaurant_id, req.data.dict())

    return {"status": "restaurant_created"}
