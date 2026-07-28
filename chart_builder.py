"""
Step 6: Given the (columns, rows) result of a query, decide the best
chart type and render it with Plotly. No second LLM call — this is a
plain heuristic based on the shape/types of the returned data, to save
API usage and keep rendering instant.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def choose_chart_type(columns: list[str], rows: list[tuple], question: str = "") -> str:
    """
    Returns one of: 'bar', 'line', 'pie', 'metric', 'table'
    """
    if not rows:
        return "table"

    df = pd.DataFrame(rows, columns=columns)

    # Single row, single column -> a single metric value
    if len(df) == 1 and len(columns) == 1:
        return "metric"

    numeric_cols = [c for c in columns if _is_numeric(df[c])]
    non_numeric_cols = [c for c in columns if c not in numeric_cols]

    # Question explicitly asks for a pie chart or a "distribution" ->
    # only valid if the shape is one categorical + one numeric column
    question_lower = question.lower()
    wants_pie = "pie" in question_lower or "distribution" in question_lower
    if wants_pie and len(non_numeric_cols) == 1 and len(numeric_cols) == 1:
        return "pie"

    # A 'year' column present + at least one numeric column -> time series
    if "year" in [c.lower() for c in columns] and numeric_cols:
        return "line"

    # One categorical + one numeric, multiple rows -> bar chart
    if len(non_numeric_cols) == 1 and len(numeric_cols) >= 1 and len(df) > 1:
        return "bar"

    # Single row with multiple numeric columns -> still best shown as a table
    if len(df) == 1:
        return "metric"

    # Fallback
    return "table"


def render_chart(columns: list[str], rows: list[tuple], question: str = "") -> go.Figure | None:
    """
    Builds a Plotly figure based on the chosen chart type.
    Returns None if the result is best shown as a plain table (caller
    should just print/display columns+rows directly in that case).
    """
    if not rows:
        return None

    df = pd.DataFrame(rows, columns=columns)
    chart_type = choose_chart_type(columns, rows)

    if chart_type == "metric":
        # Single value -> a simple indicator figure
        value = df.iloc[0, -1] if pd.api.types.is_numeric_dtype(df.iloc[:, -1]) else df.iloc[0, 0]
        label = columns[-1] if pd.api.types.is_numeric_dtype(df.iloc[:, -1]) else columns[0]
        fig = go.Figure(go.Indicator(
            mode="number",
            value=value if isinstance(value, (int, float)) else 0,
            title={"text": label},
        ))
        return fig

    if chart_type == "bar":
        non_numeric_cols = [c for c in columns if not pd.api.types.is_numeric_dtype(df[c])]
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        x_col = non_numeric_cols[0]
        y_col = numeric_cols[0]
        fig = px.bar(df, x=x_col, y=y_col, title=question)
        return fig

    if chart_type == "line":
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c]) and c.lower() != "year"]
        y_col = numeric_cols[0] if numeric_cols else columns[-1]
        fig = px.line(df, x="year" if "year" in [c.lower() for c in columns] else columns[0],
                       y=y_col, title=question, markers=True)
        return fig

    # 'table' -> no figure, caller handles it as a plain table
    return None


# ---- Quick manual test using pipeline.py's output shape ----
if __name__ == "__main__":
    # Simulated results matching what pipeline.ask() would return
    test_cases = [
        {
            "question": "average budget by genre",
            "columns": ["genre", "avg_budget"],
            "rows": [("Family", 160000000.0), ("Action", 92008196.7), ("Animation", 88483018.9)],
        },
        {
            "question": "average rating by year",
            "columns": ["year", "avg_score"],
            "rows": [(2018, 6.5), (2019, 6.7), (2020, 6.9)],
        },
        {
            "question": "total number of movies",
            "columns": ["count"],
            "rows": [(5421,)],
        },
    ]

    for case in test_cases:
        chart_type = choose_chart_type(case["columns"], case["rows"])
        print(f"Q: {case['question']} -> chart type: {chart_type}")
        fig = render_chart(case["columns"], case["rows"], case["question"])
        print(f"  Figure created: {fig is not None}")