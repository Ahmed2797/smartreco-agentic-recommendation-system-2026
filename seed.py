import sys
import os

# Project root directory fix for execution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from src.database.db import SessionLocal, engine, Base
from src.database import models

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def seed_database():
    db: Session = SessionLocal()
    try:
        print("🌱 Starting Database Seeding Process...")

        # ---------------------------------------------------------
        # 1. Seed Demo Users
        # ---------------------------------------------------------
        if db.query(models.User).count() == 0:
            demo_users = [
                models.User(
                    username="demouser",
                    email="demo@smartreco.ai",
                    hashed_password="hashed_secret_password_123"
                ),
                models.User(
                    username="alex_tech",
                    email="alex@smartreco.ai",
                    hashed_password="hashed_secret_password_456"
                )
            ]
            db.add_all(demo_users)
            db.commit()
            print("✅ Users seeded successfully.")
        else:
            print("ℹ️ Users table already contains data. Skipping user seed.")

        # ---------------------------------------------------------
        # 2. Seed Sample Product Catalog
        # ---------------------------------------------------------
        if db.query(models.Product).count() == 0:
            sample_products = [
                # Electronics / Laptops
                models.Product(
                    title="MacBook Air M2 (13-inch, 256GB)",
                    category="Electronics",
                    price=1099.99,
                    description="Supercharged by M2 chip. Thin, fast, and incredibly power efficient.",
                    image_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500&q=80"
                ),
                models.Product(
                    title="4K Ultra HD Curved Gaming Monitor 27\"",
                    category="Electronics",
                    price=349.50,
                    description="144Hz refresh rate with 1ms response time for immersive visual experience.",
                    image_url="https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&q=80"
                ),

                # Audio
                models.Product(
                    title="Sony WH-1000XM5 Wireless Headphones",
                    category="Audio",
                    price=398.00,
                    description="Industry-leading noise canceling with two processors and 8 microphones.",
                    image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&q=80"
                ),
                models.Product(
                    title="AirPods Pro (2nd Generation)",
                    category="Audio",
                    price=249.00,
                    description="Up to 2x more Active Noise Cancellation with Adaptive Audio.",
                    image_url="https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=500&q=80"
                ),

                # Wearables
                models.Product(
                    title="Apple Watch Series 9 GPS 45mm",
                    category="Wearables",
                    price=429.00,
                    description="S9 SiP enables a superbright display and magic double tap gesture.",
                    image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&q=80"
                ),
                models.Product(
                    title="Samsung Galaxy Watch 6 Classic",
                    category="Wearables",
                    price=369.99,
                    description="Advanced sleep coaching, ECG monitoring, and rotating physical bezel.",
                    image_url="https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=500&q=80"
                ),

                # Accessories
                models.Product(
                    title="Mechanical RGB Gaming Keyboard",
                    category="Accessories",
                    price=89.99,
                    description="Customizable RGB lighting with tactile mechanical switches.",
                    image_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&q=80"
                ),
                models.Product(
                    title="Ergonomic Wireless Vertical Mouse",
                    category="Accessories",
                    price=45.00,
                    description="Reduces wrist strain and improves posture during long coding sessions.",
                    image_url="https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500&q=80"
                )
            ]
            db.add_all(sample_products)
            db.commit()
            print("✅ Products catalog seeded successfully.")
        else:
            print("ℹ️ Products table already contains data. Skipping product seed.")

        print("🎉 Seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

### python seed.py