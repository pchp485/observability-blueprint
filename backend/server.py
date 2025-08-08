from fastapi import FastAPI, APIRouter, HTTPException, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
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


# ==========================
# Core Demo Models / Routes
# ==========================
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
        doc.pop('_id', None)
        try:
            cleaned.append(StatusCheck(**doc))
        except Exception as e:
            logging.warning(f"Skipping invalid document: {e}; doc={doc}")
    return cleaned


# =====================================
# Control Plane (Projects, Sinks, Agents)
# =====================================
SUPPORTED_SINK_TYPES = {"prometheus", "kafka", "otlp", "splunk_hec", "elasticsearch"}
SUPPORTED_SIGNALS = {"metrics", "logs", "traces"}
SUPPORTED_AGENT_MODES = {"agent", "agentless"}


class ProjectCreate(BaseModel):
    name: str


class Project(ProjectCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SinkCreate(BaseModel):
    name: Optional[str] = None
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None


class Sink(SinkCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentCreate(BaseModel):
    name: str
    mode: str = "agent"  # "agent" or "agentless"
    project_id: Optional[str] = None
    sink_ids: List[str] = Field(default_factory=list)
    scrape_targets: List[str] = Field(default_factory=list)  # e.g., ["host:port", "host2:port"]
    labels: Dict[str, str] = Field(default_factory=dict)


class Agent(AgentCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)


@api_router.post("/projects", response_model=Project)
async def create_project(payload: ProjectCreate):
    prj = Project(**payload.model_dump())
    try:
        await db.projects.insert_one(prj.model_dump())
    except Exception as e:
        logging.exception("Failed to insert project")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    return prj


@api_router.get("/projects", response_model=List[Project])
async def list_projects():
    items = await db.projects.find().sort("created_at", -1).to_list(1000)
    out: List[Project] = []
    for it in items:
        it.pop('_id', None)
        out.append(Project(**it))
    return out


@api_router.post("/sinks", response_model=Sink)
async def create_sink(payload: SinkCreate):
    if payload.type not in SUPPORTED_SINK_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported sink type. Allowed: {sorted(SUPPORTED_SINK_TYPES)}")
    sk = Sink(**payload.model_dump())
    try:
        await db.sinks.insert_one(sk.model_dump())
    except Exception as e:
        logging.exception("Failed to insert sink")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    return sk


@api_router.get("/sinks", response_model=List[Sink])
async def list_sinks():
    items = await db.sinks.find().sort("created_at", -1).to_list(1000)
    out: List[Sink] = []
    for it in items:
        it.pop('_id', None)
        out.append(Sink(**it))
    return out


@api_router.post("/agents", response_model=Agent)
async def create_agent(payload: AgentCreate):
    if payload.mode not in SUPPORTED_AGENT_MODES:
        raise HTTPException(status_code=400, detail=f"Unsupported agent mode. Allowed: {sorted(SUPPORTED_AGENT_MODES)}")
    # Validate sinks exist
    if payload.sink_ids:
        found_ids = set()
        async for s in db.sinks.find({"id": {"$in": payload.sink_ids}}):
            found_ids.add(s.get("id"))
        missing = set(payload.sink_ids) - found_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown sink_ids: {sorted(missing)}")

    ag = Agent(**payload.model_dump())
    try:
        await db.agents.insert_one(ag.model_dump())
    except Exception as e:
        logging.exception("Failed to insert agent")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    return ag


@api_router.get("/agents", response_model=List[Agent])
async def list_agents():
    items = await db.agents.find().sort("created_at", -1).to_list(1000)
    out: List[Agent] = []
    for it in items:
        it.pop('_id', None)
        out.append(Agent(**it))
    return out


@api_router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    doc = await db.agents.find_one({"id": agent_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    doc.pop('_id', None)
    return Agent(**doc)


@api_router.post("/agents/{agent_id}/rotate_token", response_model=Dict[str, str])
async def rotate_agent_token(agent_id: str):
    new_token = str(uuid.uuid4())
    res = await db.agents.update_one({"id": agent_id}, {"$set": {"token": new_token}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"id": agent_id, "token": new_token}


# ------------------------------
# Config Generation (OTel Collector)
# ------------------------------
class ConfigRequest(BaseModel):
    signals: List[str] = Field(default_factory=lambda: ["metrics"])  # subset of SUPPORTED_SIGNALS
    prometheus_exporter_port: Optional[int] = None  # if sink type 'prometheus' selected


def _yaml_dump_like(d: Any, indent: int = 0) -> str:
    """Very small YAML emitter for simple dict/list/scalar structures.
    Avoids external deps. Not for complex types.
    """
    sp = "  " * indent
    if isinstance(d, dict):
        lines = []
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{sp}{k}:")
                lines.append(_yaml_dump_like(v, indent + 1))
            else:
                if isinstance(v, str):
                    lines.append(f"{sp}{k}: \"{v}\"")
                else:
                    lines.append(f"{sp}{k}: {v}")
        return "\n".join(lines)
    elif isinstance(d, list):
        lines = []
        for item in d:
            if isinstance(item, (dict, list)):
                lines.append(f"{sp}-")
                lines.append(_yaml_dump_like(item, indent + 1))
            else:
                if isinstance(item, str):
                    lines.append(f"{sp}- \"{item}\"")
                else:
                    lines.append(f"{sp}- {item}")
        return "\n".join(lines)
    else:
        return f"{sp}{d}"


def _build_collector_config(agent: Agent, sinks: List[Sink], signals: List[str], prom_exporter_port: Optional[int]) -> Dict[str, Any]:
    # Receivers
    receivers: Dict[str, Any] = {
        "otlp": {
            "protocols": {
                "grpc": {"endpoint": "0.0.0.0:4317"},
                "http": {"endpoint": "0.0.0.0:4318"},
            }
        }
    }
    if agent.scrape_targets:
        receivers["prometheus"] = {
            "config": {
                "scrape_configs": [
                    {
                        "job_name": "aether-scrape",
                        "metrics_path": "/metrics",
                        "static_configs": [
                            {"targets": agent.scrape_targets}
                        ],
                    }
                ]
            }
        }

    # Processors
    processors: Dict[str, Any] = {
        "memory_limiter": {"limit_mib": 256, "spike_limit_mib": 64, "check_interval": "5s"},
        "batch": {"timeout": "1s", "send_batch_size": 512, "send_batch_max_size": 1024},
    }

    # Exporters based on sinks
    exporters: Dict[str, Any] = {}
    enabled_exporters: List[str] = []

    for s in sinks:
        if s.type == "prometheus":
            port = prom_exporter_port or 8889
            exporters["prometheus"] = {
                "endpoint": f"0.0.0.0:{port}",
                "namespace": "aether",
            }
            enabled_exporters.append("prometheus")
        elif s.type == "otlp":
            cfg = {
                "endpoint": s.config.get("endpoint", "localhost:4317"),
            }
            # allow insecure for demos
            if s.config.get("insecure", True):
                cfg["tls"] = {"insecure": True}
            exporters["otlp"] = cfg
            enabled_exporters.append("otlp")
        elif s.type == "kafka":
            exporters["kafka"] = {
                "brokers": s.config.get("brokers", ["localhost:9092"]),
                "topic": s.config.get("topic", "otlp_data"),
            }
            enabled_exporters.append("kafka")
        elif s.type == "splunk_hec":
            exporters["splunk_hec"] = {
                "token": s.config.get("token", "CHANGE_ME"),
                "endpoint": s.config.get("endpoint", "https://splunk:8088/services/collector"),
                "insecure_skip_verify": True,
            }
            enabled_exporters.append("splunk_hec")
        elif s.type == "elasticsearch":
            exporters["elasticsearch"] = {
                "endpoints": s.config.get("endpoints", ["http://elasticsearch:9200"]),
                "index": s.config.get("index", "app-logs-%{+yyyy.MM.dd}"),
            }
            enabled_exporters.append("elasticsearch")

    # Pipelines by signals
    pipelines: Dict[str, Any] = {}
    recv_list_metrics = ["otlp"] + (["prometheus"] if "prometheus" in receivers else [])

    if "metrics" in signals:
        pipelines["metrics"] = {
            "receivers": recv_list_metrics,
            "processors": ["memory_limiter", "batch"],
            "exporters": enabled_exporters or ["prometheus"],
        }
    if "logs" in signals:
        pipelines["logs"] = {
            "receivers": ["otlp"],
            "processors": ["memory_limiter", "batch"],
            "exporters": enabled_exporters or ["otlp"],
        }
    if "traces" in signals:
        pipelines["traces"] = {
            "receivers": ["otlp"],
            "processors": ["memory_limiter", "batch"],
            "exporters": enabled_exporters or ["otlp"],
        }

    cfg: Dict[str, Any] = {
        "receivers": receivers,
        "processors": processors,
        "exporters": exporters or {"prometheus": {"endpoint": f"0.0.0.0:{prom_exporter_port or 8889}"}},
        "service": {
            "pipelines": pipelines,
        },
    }
    return cfg


@api_router.post("/agents/{agent_id}/config")
async def generate_config(agent_id: str, body: ConfigRequest):
    # Load agent
    a_doc = await db.agents.find_one({"id": agent_id})
    if not a_doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    a_doc.pop('_id', None)
    agent = Agent(**a_doc)

    # Load sinks
    sinks: List[Sink] = []
    if agent.sink_ids:
        cur = db.sinks.find({"id": {"$in": agent.sink_ids}})
        async for s in cur:
            s.pop('_id', None)
            sinks.append(Sink(**s))

    # Validate signals
    signals = [s for s in body.signals if s in SUPPORTED_SIGNALS]
    if not signals:
        signals = ["metrics"]

    cfg = _build_collector_config(agent, sinks, signals, body.prometheus_exporter_port)
    yaml_text = _yaml_dump_like(cfg)
    return Response(content=yaml_text, media_type="text/yaml")


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