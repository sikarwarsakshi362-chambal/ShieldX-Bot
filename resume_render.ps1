import os
import motor.motor_asyncio

mongo_url = os.environ.get("MONGO_URI")
client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
db = client["mydb"]
print("✅ Connected to MongoDB")
