"""
Step 5: Full pipeline — takes a plain-English question, generates SQL,
validates + executes it, and retries once with the LLM if execution fails.
"""

import sqlite3
from groq import Groq
import os
from dotenv import load_dotenv

from prompt_template import build_prompt
from sql_validator import execute_sql, SQLValidationError

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def _call_llm(messages: list[dict]) -> str:
    """Sends messages to Groq and returns the cleaned SQL string."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()

    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()

    return sql


def ask(user_question: str, retry_on_failure: bool = True) -> dict:
    """
    Full pipeline: question -> SQL -> validated + executed result.

    Returns a dict:
    {
        "question": ...,
        "sql": ...,
        "columns": [...] or None,
        "rows": [...] or None,
        "error": None or a string describing what went wrong,
    }
    """
    messages = build_prompt(user_question)
    sql = _call_llm(messages)

    try:
        columns, rows = execute_sql(sql)
        return {
            "question": user_question,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "error": None,
        }

    except (SQLValidationError, sqlite3.Error) as e:
        if not retry_on_failure:
            return {
                "question": user_question,
                "sql": sql,
                "columns": None,
                "rows": None,
                "error": str(e),
            }

        # Retry once: feed the error back to the LLM and ask it to fix the SQL
        retry_messages = messages + [
            {"role": "assistant", "content": sql},
            {"role": "user", "content": (
                f"That query failed with this error: {e}. "
                f"Please return a corrected SQL query only, no explanation."
            )},
        ]
        retry_sql = _call_llm(retry_messages)

        try:
            columns, rows = execute_sql(retry_sql)
            return {
                "question": user_question,
                "sql": retry_sql,
                "columns": columns,
                "rows": rows,
                "error": None,
            }
        except (SQLValidationError, sqlite3.Error) as e2:
            return {
                "question": user_question,
                "sql": retry_sql,
                "columns": None,
                "rows": None,
                "error": f"Failed after retry: {e2}",
            }


# ---- Quick manual test ----
if __name__ == "__main__":
    test_questions = [
        "top 5 highest budget horror movies",
        "average budget by genre for movies after 2015",
        "which director has the most movies in this dataset",
    ]

    for q in test_questions:
        result = ask(q)
        print(f"Q: {result['question']}")
        print(f"SQL: {result['sql']}")
        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            print(f"Columns: {result['columns']}")
            print(f"Rows returned: {len(result['rows'])}")
            print(f"Sample: {result['rows'][:3]}")
        print()