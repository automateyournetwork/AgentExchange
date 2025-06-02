from fastapi import APIRouter, HTTPException, status
from registry_server.models import AgentCard, AgentRegisterRequest, AgentListResponse
from registry_server.storage import AgentStore

router = APIRouter()
store = AgentStore()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_agent(payload: AgentRegisterRequest):
    try:
        store.register(payload.agent, payload.owner_email)
        return {"message": "✅ Agent registered", "endpoint": payload.agent.endpoint}
    except ValueError:
        raise HTTPException(status_code=409, detail="Agent already registered at this endpoint")

@router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    return AgentListResponse(agents=store.list_agents())

@router.get("/agents/{endpoint}", response_model=AgentCard)
async def get_agent_by_endpoint(endpoint: str):
    agent = store.get_agent(endpoint)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
