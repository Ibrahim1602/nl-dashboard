import json
import os
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

ALLOWED_CHART_TYPES = {"bar", "line", "pie", "scatter", "area", "histogram", "metric", "table"}

def _describe_columns(df: pd.DataFrame) -> str:
    """One line per column: name, whether it's numeric or categorical, and a few example values."""
    lines = []
    for col in df.columns:
        dtype = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "categorical/text"
        sample_vals = df[col].dropna().unique()[:3].tolist()
        lines.append(f"- {col} ({dtype}), example values: {sample_vals}")
    return "\n".join(lines)


def _build_planning_prompt(question: str, df: pd.DataFrame) -> list[dict]:
    system_prompt = f"""You are a data visualization assistant. Given a user's question and
the shape of the query result that answers it, decide the single best way to
visualize it.

Available chart types: bar, line, pie, scatter, area, histogram, metric, table.
- "metric": a single number as a headline stat (only if the result is a single row
  and the meaningful value is one number).
- "table": use only if no chart would clarify the data better than reading it directly.

Result has {len(df)} row(s) and these columns:
{_describe_columns(df)}

Respond with ONLY a JSON object, no explanation, no markdown fences, in this exact shape:
{{
  "chart_type": one of {sorted(ALLOWED_CHART_TYPES)},
  "x": "<column name or null>",
  "y": "<column name or null>",
  "color": "<column name or null, for grouping/legend>",
  "title": "<short human-readable chart title>"
}}

Rules:
- x, y, color must be exact column names from the list above, or null.
- Prefer "pie" when the user asks for a pie chart, breakdown, or share of a small
  number of categories (roughly 2-8).
- Prefer "line" when there's a clear time/sequence column (like year) and a numeric value.
- Prefer "bar" for comparing a numeric value across categories, especially with more
  than 8 categories or when ranking (e.g. top N).
- Prefer "scatter" when comparing two numeric columns with no ranking or category.
- Use "metric" for a single aggregate number.
- Use "table" when the result is mostly text/detail meant to be read row by row.
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f'User question: "{question}"'},
    ]


def _validate_plan(plan: dict, columns: list[str]) -> dict | None:
    if not isinstance(plan, dict):
        return None

    chart_type = plan.get("chart_type")
    if chart_type not in ALLOWED_CHART_TYPES:
        return None

    for key in ("x", "y", "color"):
        val = plan.get(key)
        if val is not None and val not in columns:
            plan[key] = None

    plan.setdefault("title", "")
    return plan


def plan_chart(question: str, columns: list[str], rows: list[tuple]) -> dict | None:
    if not rows:
        return None

    df = pd.DataFrame(rows, columns=columns)
    messages = _build_planning_prompt(question, df)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        plan = json.loads(raw)
    except Exception:
        return None

    return _validate_plan(plan, columns)