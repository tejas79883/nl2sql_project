"""
main.py
FastAPI application for the NL2SQL Clinic Chatbot.

Endpoints:
  POST /chat   – Ask a natural language question, get SQL + results + chart
  GET  /health – Health check with DB connectivity and memory stats
"""

import os
import re
import sqlite3
import asyncio
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from vanna_setup import get_agent
from sql_validator import validate_sql, SQLValidationError
from vanna.core.user import User
from vanna.core.user.request_context import RequestContext
from vanna.components import (
    DataFrameComponent,
    ChartComponent,
    RichTextComponent,
    SimpleTextComponent,
)


DB_PATH = os.getenv("DB_PATH", "clinic.db")

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NL2SQL Clinic Chatbot",
    description="Natural Language to SQL chatbot for a clinic management database, powered by Vanna 2.0 + Groq.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    message: str
    sql_query: Optional[str] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[list[Any]]] = None
    row_count: Optional[int] = None
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract SQL from agent response text
# ─────────────────────────────────────────────────────────────────────────────
_SQL_FENCE_RE = re.compile(
    r"```(?:sql)?\s*(SELECT[\s\S]+?)```",
    re.IGNORECASE,
)
_SQL_INLINE_RE = re.compile(
    r"\b(SELECT\s[\s\S]+?;)",
    re.IGNORECASE,
)


def _extract_sql(text: str) -> Optional[str]:
    """Pull the first SQL SELECT statement from a block of text."""
    m = _SQL_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    m = _SQL_INLINE_RE.search(text)
    if m:
        return m.group(1).strip()
    return None


def _run_sql_direct(sql: str) -> tuple[list[str], list[list[Any]]]:
    """
    Execute a validated SELECT against clinic.db directly.
    Returns (columns, rows).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        rows_raw = cur.fetchall()
        if not rows_raw:
            return [], []
        columns = list(rows_raw[0].keys())
        rows    = [list(r) for r in rows_raw]
        return columns, rows
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# POST /chat
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    agent = get_agent()

    request_context = RequestContext()
    conversation_id = str(uuid.uuid4())

    # ── Collect all components from the agent's async generator ──────────────
    text_parts: list[str] = []
    sql_found:  Optional[str] = None
    df_component: Optional[DataFrameComponent] = None
    chart_component: Optional[ChartComponent]  = None

    try:
        async for component in agent.send_message(
            request_context=request_context,
            message=question,
            conversation_id=conversation_id,
        ):
            ctype = getattr(component, "type", None)

            # Text / rich-text responses
            if hasattr(component, "text"):
                text_parts.append(component.text)
            elif hasattr(component, "content"):
                text_parts.append(str(component.content))

            # DataFrame component (contains columns + rows)
            if isinstance(component, DataFrameComponent):
                df_component = component

            # Chart component
            if isinstance(component, ChartComponent):
                chart_component = component

    except Exception as agent_err:
        return ChatResponse(
            message="The AI agent encountered an error while processing your question.",
            error=str(agent_err),
        )

    full_text = " ".join(text_parts).strip()

    # ── Try to find SQL in the agent's textual output ─────────────────────────
    if sql_found is None:
        sql_found = _extract_sql(full_text)

    # ── Validate the SQL before (re-)executing ────────────────────────────────
    validated_sql: Optional[str] = None
    if sql_found:
        try:
            validated_sql = validate_sql(sql_found)
        except SQLValidationError as ve:
            return ChatResponse(
                message="The AI generated a query that failed security validation.",
                sql_query=sql_found,
                error=str(ve),
            )

    # ── Execute SQL and build the response ─────────────────────────────────────
    columns: list[str] = []
    rows:    list[list[Any]] = []

    # Prefer agent-provided DataFrame
    if df_component is not None:
        columns = df_component.columns
        rows    = [[row.get(c) for c in columns] for row in df_component.rows]

    # Fall back to direct execution when agent didn't return a DataFrame
    elif validated_sql:
        try:
            columns, rows = _run_sql_direct(validated_sql)
        except sqlite3.Error as db_err:
            return ChatResponse(
                message="The SQL query failed to execute against the database.",
                sql_query=validated_sql,
                error=str(db_err),
            )

    row_count = len(rows)

    # ── Build the final message ───────────────────────────────────────────────
    if not full_text:
        if row_count == 0:
            full_text = "No data found for your query."
        else:
            full_text = f"Here are the results for: {question}"

    # ── Chart ────────────────────────────────────────────────────────────────
    chart_payload  = None
    chart_type_str = None
    if chart_component is not None:
        chart_payload  = chart_component.data
        chart_type_str = chart_component.chart_type

    return ChatResponse(
        message=full_text,
        sql_query=validated_sql,
        columns=columns if columns else None,
        rows=rows if rows else None,
        row_count=row_count if columns else None,
        chart=chart_payload,
        chart_type=chart_type_str,
    )





# ─────────────────────────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health") 
async def health():
    # Check DB connectivity
    db_status = "connected"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT COUNT(*) FROM patients")
        conn.close()
    except Exception as e:
        db_status = f"error: {e}"

    # Count seeded memory items
    agent  = get_agent()
    memory = agent.agent_memory
    try:
        mem_count = len(memory._memories)
    except Exception:
        mem_count = -1

    return {
        "status": "ok",
        "database": db_status,
        "agent_memory_items": mem_count,
        "db_path": DB_PATH,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "NL2SQL Clinic Chatbot API is running.",
        "docs": "/docs",
        "health": "/health",
        "chat": "POST /chat  →  { \"question\": \"...\" }",
    }
