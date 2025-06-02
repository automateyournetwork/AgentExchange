from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class AgentSkill(BaseModel):
    id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    tags: Optional[List[str]] = Field(default_factory=list)


class AgentCapabilities(BaseModel):
    a2a: bool = True
    toolUse: bool = True
    chat: bool = True
    streaming: bool = False
    push: bool = False


class AgentCard(BaseModel):
    name: str
    description: Optional[str]
    version: str = "1.0.0"
    url: HttpUrl
    endpoint: HttpUrl
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    capabilities: AgentCapabilities
    skills: List[AgentSkill]


class AgentRegisterRequest(BaseModel):
    agent: AgentCard
    owner_email: Optional[str] = Field(None, description="Email of the person or service registering this agent")


class AgentListResponse(BaseModel):
    agents: List[AgentCard]
