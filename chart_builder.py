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


def render_chart_from_plan(df: pd.DataFrame, plan: dict) -> go.Figure | None:
    """
    Builds a Plotly figure directly from an LLM-produced plan
    (see chart_planner.plan_chart). No guessing — just executes it.
    """
    chart_type = plan["chart_type"]
    x, y, color = plan.get("x"), plan.get("y"), plan.get("color")
    title = plan.get("title", "")

    if chart_type == "table":
        return None

    if chart_type == "metric":
        value_col = y or x or df.columns[-1]
        value = df.iloc[0][value_col]
        fig = go.Figure(go.Indicator(
            mode="number",
            value=value if isinstance(value, (int, float)) else 0,
            title={"text": title or value_col},
        ))
        return fig

    if chart_type == "pie":
        names = x or df.columns[0]
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        values = y or (numeric_cols[0] if numeric_cols else df.columns[-1])

        # Cap slice count so tiny categories don't turn into an unreadable
        # wall of labels — group anything past the top N into "Other".
        MAX_SLICES = 8
        if len(df) > MAX_SLICES:
            df_sorted = df.sort_values(values, ascending=False)
            top = df_sorted.iloc[:MAX_SLICES - 1]
            rest_total = df_sorted.iloc[MAX_SLICES - 1:][values].sum()
            other_row = {names: "Other", values: rest_total}
            df = pd.concat([top, pd.DataFrame([other_row])], ignore_index=True)

        try:
            return px.pie(df, names=names, values=values, title=title)
        except Exception:
            return None

    if chart_type == "bar":
        MAX_BARS = 20
        if len(df) > MAX_BARS and y in df.columns:
            df = df.sort_values(y, ascending=False).iloc[:MAX_BARS]
            title = f"{title} (top {MAX_BARS})" if title else f"Top {MAX_BARS}"


    plot_fn = {
        "bar": px.bar,
        "line": px.line,
        "scatter": px.scatter,
        "area": px.area,
        "histogram": px.histogram,
    }.get(chart_type)

    if plot_fn is None:
        return None

    kwargs = {"title": title}
    if x:
        kwargs["x"] = x
    if y:
        kwargs["y"] = y
    if color:
        kwargs["color"] = color
    if chart_type == "line":
        kwargs["markers"] = True

    try:
        return plot_fn(df, **kwargs)
    except Exception:
        return None

