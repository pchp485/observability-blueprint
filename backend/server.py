from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.get("/health")
async def health():
    """Lightweight health endpoint that also attempts a Mongo ping."""
    db_ok = False
    try:
        # Mongo ping (does not create collections)
        res = await db.command('ping')
        db_ok = res.get('ok', 0) == 1
    except Exception as e:
        logging.warning(f"Mongo ping failed: {e}")
        db_ok = False
    return {
        "status": "ok",
        "db": "ok" if db_ok else "unavailable",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    try:
        await db.status_checks.insert_one(status_obj.model_dump())
    except Exception as e:
        logging.exception("Failed to insert status check")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    try:
        status_checks = await db.status_checks.find().sort("timestamp", -1).limit(1000).to_list(1000)
    except Exception as e:
        logging.exception("Failed to fetch status checks")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    cleaned: List[StatusCheck] = []
    for doc in status_checks:
        # Ensure Mongo's _id does not break Pydantic parsing
        doc.pop('_id', None)
        try:
            cleaned.append(StatusCheck(**doc))
        except Exception as e:
            logging.warning(f"Skipping invalid document: {e}; doc={doc}")
    return cleaned


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()