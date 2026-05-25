from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: Optional[AsyncIOMotorClient] = None

db = Database()

async def get_database():
    if db.client is None:
        raise RuntimeError("Database client is not initialized. Call connect_to_mongo() first.")
    return db.client[settings.DATABASE_NAME]

async def init_indexes():
    """
    Creates indexes for the database collections to ensure performance and uniqueness.
    """
    if db.client is None:
        raise RuntimeError("Database client is not initialized. Call connect_to_mongo() first.")
    database = db.client[settings.DATABASE_NAME]
    
    # 1. Users
    await database["users"].create_index("email", unique=True)
    await database["users"].create_index("referral_code", unique=True, sparse=True)
    
    # 2. Credit Transactions
    await database["credit_transactions"].create_index("user_id")
    await database["credit_transactions"].create_index([("created_at", -1)])
    
    print("Indexes initialized.")

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    print("Connected to MongoDB")
    try:
        await init_indexes()
    except Exception as e:
        print(f"WARNING: Failed to initialize indexes on startup: {e}")
        print("The application will continue — indexes will be created when the database becomes available.")

async def close_mongo_connection():
    if db.client is not None:
        db.client.close()
        print("Closed MongoDB connection")