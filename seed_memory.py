"""
seed_memory.py
Pre-seeds the Vanna 2.0 DemoAgentMemory with 15 known good
question → SQL pairs so the agent has a strong head-start.

Run this ONCE after setup_database.py:
    python seed_memory.py
"""

import asyncio
import uuid
from vanna_setup import get_agent
from vanna.core.tool import ToolContext
from vanna.core.user import User

# ─────────────────────────────────────────────────────────────────────────────
# 15 Question → SQL pairs covering all required categories
# ─────────────────────────────────────────────────────────────────────────────
QA_PAIRS = [
    # ── Patient queries ───────────────────────────────────────────────────────
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients;",
    },
    {
        "question": "List all patients with their city and gender",
        "sql": (
            "SELECT first_name, last_name, city, gender "
            "FROM patients ORDER BY last_name, first_name;"
        ),
    },
    {
        "question": "How many female patients are registered?",
        "sql": "SELECT COUNT(*) AS female_patients FROM patients WHERE gender = 'F';",
    },
    {
        "question": "Which city has the most patients?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients "
            "GROUP BY city "
            "ORDER BY patient_count DESC "
            "LIMIT 1;"
        ),
    },
    {
        "question": "List patients who visited more than 3 times",
        "sql": (
            "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count "
            "FROM patients p "
            "JOIN appointments a ON a.patient_id = p.id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "HAVING COUNT(a.id) > 3 "
            "ORDER BY visit_count DESC;"
        ),
    },
    # ── Doctor queries ────────────────────────────────────────────────────────
    {
        "question": "List all doctors and their specializations",
        "sql": (
            "SELECT name, specialization, department "
            "FROM doctors ORDER BY specialization, name;"
        ),
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": (
            "SELECT d.name, d.specialization, COUNT(a.id) AS appointment_count "
            "FROM doctors d "
            "JOIN appointments a ON a.doctor_id = d.id "
            "GROUP BY d.id, d.name, d.specialization "
            "ORDER BY appointment_count DESC "
            "LIMIT 1;"
        ),
    },
    # ── Appointment queries ───────────────────────────────────────────────────
    {
        "question": "Show me appointments for last month",
        "sql": (
            "SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name, "
            "d.name AS doctor_name, a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE strftime('%Y-%m', a.appointment_date) = "
            "strftime('%Y-%m', date('now', '-1 month')) "
            "ORDER BY a.appointment_date;"
        ),
    },
    {
        "question": "How many cancelled appointments last quarter?",
        "sql": (
            "SELECT COUNT(*) AS cancelled_count "
            "FROM appointments "
            "WHERE status = 'Cancelled' "
            "AND appointment_date >= date('now', '-3 months');"
        ),
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": (
            "SELECT strftime('%Y-%m', appointment_date) AS month, "
            "COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month "
            "ORDER BY month;"
        ),
    },
    # ── Financial queries ─────────────────────────────────────────────────────
    {
        "question": "What is the total revenue?",
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices WHERE status = 'Paid';",
    },
    {
        "question": "Show revenue by doctor",
        "sql": (
            "SELECT d.name AS doctor_name, SUM(i.total_amount) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY total_revenue DESC;"
        ),
    },
    {
        "question": "Show unpaid invoices",
        "sql": (
            "SELECT i.id, p.first_name || ' ' || p.last_name AS patient_name, "
            "i.invoice_date, i.total_amount, i.paid_amount, i.status "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.invoice_date DESC;"
        ),
    },
    # ── Time-based queries ────────────────────────────────────────────────────
    {
        "question": "Top 5 patients by total spending",
        "sql": (
            "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "ORDER BY total_spending DESC "
            "LIMIT 5;"
        ),
    },
    {
        "question": "Show patient registration trend by month",
        "sql": (
            "SELECT strftime('%Y-%m', registered_date) AS month, "
            "COUNT(*) AS new_patients "
            "FROM patients "
            "GROUP BY month "
            "ORDER BY month;"
        ),
    },
]


async def seed():
    agent = get_agent()
    memory = agent.agent_memory   # DemoAgentMemory instance

    # Minimal ToolContext required by save_tool_usage
    dummy_user = User(id="seed_script", username="seed_script", group_memberships=["user"])
    ctx = ToolContext(
        user=dummy_user,
        conversation_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        agent_memory=memory,
    )

    print(f"Seeding {len(QA_PAIRS)} question–SQL pairs into DemoAgentMemory…\n")

    for i, pair in enumerate(QA_PAIRS, 1):
        await memory.save_tool_usage(
            question=pair["question"],
            tool_name="run_sql",
            args={"sql": pair["sql"]},
            context=ctx,
            success=True,
            metadata={"source": "seed_script", "index": i},
        )
        print(f"  [{i:02d}] {pair['question']}")

    # Verify
    all_memories = memory._memories   # inspect private list for count
    print(f"\n✅ Agent memory now contains {len(all_memories)} seeded entries.")
    print("Run the API server next:  uvicorn main:app --port 8000 --reload")


if __name__ == "__main__":
    asyncio.run(seed())
