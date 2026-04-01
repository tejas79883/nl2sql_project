"""
sql_validator.py
Validates AI-generated SQL before execution.
Only SELECT queries on non-system tables are allowed.
"""

import re

# ─────────────────────────────────────────────────────────────────────────────
# Blocklists
# ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN_STATEMENTS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE", "EXEC", "EXECUTE",
]

FORBIDDEN_KEYWORDS = [
    "xp_", "sp_", "GRANT", "REVOKE", "SHUTDOWN",
    "ATTACH", "DETACH", "PRAGMA",
]

FORBIDDEN_TABLES = [
    "sqlite_master", "sqlite_temp_master", "sqlite_sequence",
    "information_schema", r"sys\.", "pg_",
]


class SQLValidationError(ValueError):
    """Raised when a SQL query fails validation."""


def validate_sql(sql: str) -> str:
    """
    Validate and clean a SQL query.
    Returns the stripped SQL string if valid.
    Raises SQLValidationError with a descriptive message if invalid.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query received.")

    cleaned = sql.strip().rstrip(";")

    # ── Must start with SELECT ────────────────────────────────────────────────
    first_token = cleaned.split()[0].upper() if cleaned.split() else ""
    if first_token != "SELECT":
        raise SQLValidationError(
            f"Only SELECT statements are allowed. Got: '{first_token}'"
        )

    upper_sql = cleaned.upper()

    # ── Check for forbidden DML / DDL statements ──────────────────────────────
    for stmt in FORBIDDEN_STATEMENTS:
        # Use word boundary to avoid false positives (e.g. "EXECUTOR" ≠ "EXEC")
        pattern = r"\b" + stmt + r"\b"
        if re.search(pattern, upper_sql):
            raise SQLValidationError(
                f"Forbidden SQL statement detected: '{stmt}'. "
                "Only read-only SELECT queries are permitted."
            )

    # ── Check for dangerous keywords ──────────────────────────────────────────
    for kw in FORBIDDEN_KEYWORDS:
        if kw.upper() in upper_sql:
            raise SQLValidationError(
                f"Forbidden keyword detected: '{kw}'. Query rejected for security."
            )

    # ── Check for system table access ─────────────────────────────────────────
    for table_pattern in FORBIDDEN_TABLES:
        if re.search(table_pattern, upper_sql, re.IGNORECASE):
            raise SQLValidationError(
                f"Access to system/internal tables is not allowed: '{table_pattern}'"
            )

    # ── Basic sanity: must reference at least one FROM / JOIN ────────────────
    if "FROM" not in upper_sql:
        raise SQLValidationError(
            "SQL query must contain a FROM clause."
        )

    return cleaned
