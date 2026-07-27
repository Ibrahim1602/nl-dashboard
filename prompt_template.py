"""
Step 2: Prompt template for natural-language-to-SQL generation.

This module defines the schema description and few-shot examples that get
injected into every LLM call. No RAG, no vector DB — the full schema is
small enough to hardcode directly into the prompt every time.
"""

SCHEMA_DESCRIPTION = """
Table: movies
- name (TEXT): movie title
- rating (TEXT): MPAA content rating — one of G, PG, PG-13, R, NC-17
- genre (TEXT): primary genre, e.g. Drama, Action, Comedy
- year (INTEGER): release year, e.g. 1994
- score (REAL): audience rating out of 10
- votes (INTEGER): number of user votes
- director (TEXT): film director's name
- writer (TEXT): film writer's name
- star (TEXT): lead actor's name
- country (TEXT): country of production
- budget (INTEGER): production budget in USD
- gross (INTEGER): box office gross revenue in USD
- company (TEXT): production company
- runtime (REAL): duration in minutes
"""

# Few-shot examples: deliberately varied query patterns so the model
# generalizes rather than just pattern-matching similar phrasing.
FEW_SHOT_EXAMPLES = [
    {
        "question": "top 5 highest rated movies",
        "sql": "SELECT name, score FROM movies ORDER BY score DESC LIMIT 5;"
    },
    {
        "question": "average budget by genre",
        "sql": "SELECT genre, AVG(budget) AS avg_budget FROM movies GROUP BY genre ORDER BY avg_budget DESC;"
    },
    {
        "question": "top 10 highest grossing movies released after 2010",
        "sql": "SELECT name, gross, year FROM movies WHERE year > 2010 ORDER BY gross DESC LIMIT 10;"
    },
    {
        "question": "movies directed by Christopher Nolan",
        "sql": "SELECT name, year, score FROM movies WHERE director LIKE '%Nolan%' ORDER BY year;"
    },
    {
        "question": "action movies with a budget over 100 million and rating above 7",
        "sql": "SELECT name, budget, score FROM movies WHERE genre = 'Action' AND budget > 100000000 AND score > 7 ORDER BY score DESC;"
    },
]


def build_prompt(user_question: str) -> list[dict]:
    """
    Builds the full message list to send to the LLM, combining the
    system instructions, schema, few-shot examples, and the user's
    actual question.
    """
    examples_text = "\n\n".join(
        f"Q: \"{ex['question']}\"\nA: {ex['sql']}"
        for ex in FEW_SHOT_EXAMPLES
    )

    system_prompt = f"""You are a SQL generator. You translate natural language questions into
valid SQLite SELECT queries against the schema below.

{SCHEMA_DESCRIPTION}

Rules:
- Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
- Only use tables and columns that exist in the schema above.
- Return ONLY the raw SQL query. No explanation, no markdown code fences, no extra text.
- If the question cannot be answered with the given schema, return: SELECT 'UNSUPPORTED' AS error;

Examples:
{examples_text}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_question},
    ]


# ---- Quick manual test (no API call yet — just prints the prompt) ----
if __name__ == "__main__":
    test_question = "which movies have the most votes"
    messages = build_prompt(test_question)
    print("=== SYSTEM PROMPT ===")
    print(messages[0]["content"])
    print("\n=== USER QUESTION ===")
    print(messages[1]["content"])
