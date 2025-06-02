from typing import Dict, Optional, List
from datetime import datetime

from registry_server.models import AgentCard

class AgentStore:
    def __init__(self):
        # In-memory store: key = endpoint URL
        self._agents: Dict[str, dict] = {}

    def register(self, agent: AgentCard, owner_email: Optional[str] = None) -> None:
        if agent.endpoint in self._agents:
            raise ValueError("Agent already registered at this endpoint.")
        
        self._agents[agent.endpoint] = {
            "agent": agent,
            "owner_email": owner_email,
            "registered_at": datetime.utcnow().isoformat()
        }

    def list_agents(self) -> List[AgentCard]:
        return [entry["agent"] for entry in self._agents.values()]

    def get_agent(self, endpoint: str) -> Optional[AgentCard]:
        if endpoint not in self._agents:
            return None
        return self._agents[endpoint]["agent"]

    def exists(self, endpoint: str) -> bool:
        return endpoint in self._agents

    def get_metadata(self, endpoint: str) -> Optional[dict]:
        return self._agents.get(endpoint, None)
