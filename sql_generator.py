import os
from dotenv import load_dotenv
from groq import Groq
from prompt_template import build_prompt

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"


def generate_sql(user_question: str) -> str:
    messages = build_prompt(user_question)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,  # we want deterministic output since these are queries
    )

    sql = response.choices[0].message.content.strip()

    # stripping unnecessary markdown code fences
    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()

    return sql


# test run
if __name__ == "__main__":
    test_questions = [
        "which movies have the most votes",
        "top 5 highest rated action movies",
        "average runtime by genre",
    ]

    for q in test_questions:
        print(f"Q: {q}")
        sql = generate_sql(q)
        print(f"SQL: {sql}\n")