import sys
import os
import json
from sqlalchemy.orm import Session
from datetime import datetime

# Root directory path correction
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../")
    )
)

from src.database.db import SessionLocal, engine, Base
from src.database import models
from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import upsert_product_to_vector_db



def get_user_events_from_db(user_id: int, db: Session, limit: int = 10) -> list[dict]:
    """
    Fetches recent activity history for a given user from SQLite/PostgreSQL DB.
    """
    activities = (
        db.query(models.UserActivity)
        .filter(models.UserActivity.user_id == user_id)
        .order_by(models.UserActivity.created_at.desc())
        .limit(limit)
        .all()
    )

    # Transform database models into dictionary list matching MOCK structure
    return [
        {
            "user_id": act.user_id,
            "event_type": act.event_type,
            "event_data": act.event_data,
            "product_id": act.product_id
        }
        for act in activities
    ]

# ================================
# Demo User Events
# ================================
MOCK_EVENTS_USER_1 = [
    {
        "user_id": 1,
        "event_type": "view_page",
        "event_data": "/dashboard",
        "product_id": None
    },
    {
        "user_id": 1,
        "event_type": "search_query",
        "event_data": "AI and Machine Learning",
        "product_id": None
    },
    {
        "user_id": 1,
        "event_type": "product_click",
        "event_data": "Viewed Machine Learning Specialization",
        "product_id": 1
    },
    {
        "user_id": 1,
        "event_type": "search_query",
        "event_data": "LangChain RAG agents",
        "product_id": None
    },
    {
        "user_id": 1,
        "event_type": "product_click",
        "event_data": "Viewed LangChain & LlamaIndex Course",
        "product_id": 4
    }
]


def seed_database_and_pinecone():
    print("🚀 Starting SmartReco Seed Process...")

    # Create tables
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    inserted_products = 0

    try:
        # =====================================
        # 1. Create Demo User
        # =====================================
        existing_user = db.query(models.User).filter_by(id=1).first()
        if not existing_user:
            demo_user = models.User(
                id=1,
                email="user@smartreco.ai",
                password="mockpasswordhash",
                role="user"
            )
            db.add(demo_user)
            print("✅ Demo User created")

        # =====================================
        # 2. Load Products JSON
        # =====================================
        json_path = os.path.join(os.path.dirname(__file__), "courses.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Missing file: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            products = json.load(f)

        print(f"📦 Found {len(products)} products")

        # =====================================
        # 3. Insert Products + Embeddings
        # =====================================
        for p_data in products:
            existing_product = db.query(models.Product).filter_by(id=p_data["id"]).first()

            if not existing_product:
                product = models.Product(
                    id=p_data["id"],
                    title=p_data["title"],
                    description=p_data["description"],
                    category=p_data["category"],
                    price=float(p_data["price"])
                )
                db.add(product)
                inserted_products += 1

                # Try/Except Block inside 'if not existing_product'
                try:
                    text = f"{p_data['title']} {p_data['description']} Category: {p_data['category']}"
                    vector = get_text_embedding(text)

                    metadata = {
                        "title": p_data["title"],
                        "category": p_data["category"],
                        "price": float(p_data["price"])
                    }

                    upsert_product_to_vector_db(
                        product_id=str(p_data["id"]),
                        vector=vector,
                        metadata=metadata
                    )
                    print(f"✅ Embedded Product {p_data['id']}")

                except Exception as e:
                    print(f"⚠️ Vector DB Error for Product {p_data['id']}: {e}")

        db.commit()
        print(f"✅ New Products Added: {inserted_products}")

        # =====================================
        # 4. Insert User Events (Avoid Duplicates)
        # =====================================
        new_events = 0
        for event in MOCK_EVENTS_USER_1:
            existing_event = db.query(models.UserActivity).filter_by(
                user_id=event["user_id"],
                event_type=event["event_type"],
                event_data=event["event_data"]
            ).first()

            if not existing_event:
                db_event = models.UserActivity(
                    user_id=event["user_id"],
                    product_id=event["product_id"],
                    event_type=event["event_type"],
                    event_data=event["event_data"],
                    created_at=datetime.now()
                )
                db.add(db_event)
                new_events += 1

        db.commit()
        print(f"✅ New Events Added: {new_events}")
        print("\n🎉 SmartReco Seeding Completed!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database_and_pinecone()

## python -m Data.mock_data