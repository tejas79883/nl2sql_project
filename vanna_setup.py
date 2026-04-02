"""
vanna_setup.py
Initialises the Vanna 2.0 Agent with:
  - Groq LLM (llama-3.3-70b-versatile) via OpenAI-compatible endpoint
  - SqliteRunner for database execution
  - RunSqlTool + VisualizeDataTool + Agent-memory tools
  - DemoAgentMemory (in-process vector store)
  - Simple default UserResolver
"""

import os
from dotenv import load_dotenv

load_dotenv()

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import User
from vanna.core.user.resolver import UserResolver
from vanna.core.user.request_context import RequestContext
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool

DB_PATH = os.getenv("DB_PATH", "clinic.db")

# ─────────────────────────────────────────────────────────────────────────────
# 1. LLM Service  –  Groq (OpenAI-compatible)
# ─────────────────────────────────────────────────────────────────────────────
def create_llm_service() -> OpenAILlmService:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is not set. "
            "Create a free key at https://console.groq.com and add it to .env"
        )
    return OpenAILlmService(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Default UserResolver  –  every request maps to the same "clinic_user"
# ─────────────────────────────────────────────────────────────────────────────
class DefaultUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="clinic_user",
            username="clinic_user",
            email="clinic@example.com",
            group_memberships=["user"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Build the full Vanna 2.0 Agent
# ─────────────────────────────────────────────────────────────────────────────
def create_agent() -> Agent:
    # LLM
    llm_service = create_llm_service()

    # Database runner
    sql_runner = SqliteRunner(database_path=DB_PATH)

    # Agent memory (in-process)
    agent_memory = DemoAgentMemory(max_items=10_000)

    # Tool registry
    registry = ToolRegistry()
    registry.register_local_tool(RunSqlTool(sql_runner=sql_runner),          access_groups=["user"])
    registry.register_local_tool(VisualizeDataTool(),                         access_groups=["user"])
    registry.register_local_tool(SaveQuestionToolArgsTool(),                  access_groups=["user"])
    registry.register_local_tool(SearchSavedCorrectToolUsesTool(),            access_groups=["user"])

    # Agent config
    config = AgentConfig(
        max_tool_iterations=10,
        stream_responses=True,
        auto_save_conversations=True,
        temperature=0.2,         # lower = more deterministic SQL

       
    )

    # Assemble agent
    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,
        user_resolver=DefaultUserResolver(),
        agent_memory=agent_memory,
        config=config,
    )

    return agent


# ─────────────────────────────────────────────────────────────────────────────
# Singleton helper used by main.py and seed_memory.py
# ─────────────────────────────────────────────────────────────────────────────
_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
