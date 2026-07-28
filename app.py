from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import ask
from chart_builder import choose_chart_type, render_chart

app = FastAPI(title="NL-to-Dashboard API")

# Allow requests from any frontend for now (tighten this once you know
# your actual deployed frontend URL, e.g. allow_origins=["https://yourapp.vercel.app"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: list[str] | None
    rows: list[list] | None
    chart_type: str
    chart_json: str | None
    error: str | None


@app.get("/")
def health_check():
    """Simple endpoint to confirm the API is alive."""
    return {"status": "ok", "message": "NL-to-Dashboard API is running"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Takes a plain-English question, runs it through the full pipeline,
    and returns the SQL, raw results, and a ready-to-render chart (as
    Plotly JSON) if applicable.
    """
    result = ask(request.question)

    chart_type = "table"
    chart_json = None

    if result["error"] is None and result["rows"]:
        chart_type = choose_chart_type(result["columns"], result["rows"])
        fig = render_chart(result["columns"], result["rows"], request.question)
        if fig is not None:
            chart_json = fig.to_json()

    return QueryResponse(
        question=result["question"],
        sql=result["sql"],
        columns=result["columns"],
        rows=[list(r) for r in result["rows"]] if result["rows"] else None,
        chart_type=chart_type,
        chart_json=chart_json,
        error=result["error"],
    )