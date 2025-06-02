from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document

from pathlib import Path

class AgentStore:
    def __init__(self, persist_path: str = "rag_index"):
        self._agents: Dict[str, dict] = {}
        self.persist_path = persist_path
        self.vector_store = Chroma(
            persist_directory=persist_path,
            embedding_function=OpenAIEmbeddings()
        )

    def _agent_to_document(self, agent: AgentCard) -> Document:
        content = f"Agent {agent.name}: {agent.description or ''} " \
                  f"Tools: {[skill.name for skill in agent.skills or []]}"
        return Document(page_content=content, metadata={"endpoint": agent.endpoint})

    def register(self, agent: AgentCard, owner_email: Optional[str] = None) -> None:
        if agent.endpoint in self._agents:
            raise ValueError("Agent already registered at this endpoint.")

        self._agents[agent.endpoint] = {
            "agent": agent,
            "owner_email": owner_email,
            "registered_at": datetime.utcnow().isoformat()
        }

        doc = self._agent_to_document(agent)
        self.vector_store.add_documents([doc])
        self.vector_store.persist()

    def query(self, text: str, k: int = 3) -> List[AgentCard]:
        results = self.vector_store.similarity_search(text, k=k)
        return [self._agents[r.metadata["endpoint"]]["agent"] for r in results]
