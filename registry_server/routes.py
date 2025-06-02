from fastapi import APIRouter, HTTPException, status, Query
from registry_server.models import AgentCard, AgentRegisterRequest, AgentListResponse
from registry_server.storage import AGENT_STORE

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_agent(payload: AgentRegisterRequest):
    try:
        AGENT_STORE.register(payload.agent, payload.owner_email)
        return {"message": "✅ Agent registered", "endpoint": payload.agent.endpoint}
    except ValueError:
        raise HTTPException(status_code=409, detail="Agent already registered at this endpoint")

@router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    return AgentListResponse(agents=AGENT_STORE.list_agents())

@router.get("/agents/{endpoint}", response_model=AgentCard)
async def get_agent_by_endpoint(endpoint: str):
    agent = AGENT_STORE.get_agent(endpoint)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/agents/search", response_model=AgentListResponse)
async def search_agents(q: str = Query(..., description="Natural language search for agents")):
    results = AGENT_STORE.query(q)
    return AgentListResponse(agents=results)
