import httpx
from typing import Optional
from a2a.types import AgentCard


async def fetch_agent_card(endpoint: str) -> Optional[AgentCard]:
    """
    Fetch the agent card from the given endpoint.
    """
    url = endpoint.rstrip("/") + "/.well-known/agent.json"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return AgentCard(**data)
    except Exception as e:
        print(f"❌ Failed to fetch agent card from {url}: {e}")
        return None


def normalize_url(url: str) -> str:
    """
    Ensure the endpoint URL ends without a trailing slash.
    """
    return url.rstrip("/")
