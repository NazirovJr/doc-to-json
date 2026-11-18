import os

import ollama

from .schema import Answer

MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6-35b-a3b-agent")
VALUE_CONSTRAINTS = {"format", "pattern", "minLength", "minimum", "maximum"}


def _structure_only(schema):
    """Грамматика не проверяет значения, а подгоняет под них ответ («12.11.2026» -> «1211-11-20»),
    поэтому ей отдаётся только структура, а значения проверяет pydantic."""
    if isinstance(schema, dict):
        return {key: _structure_only(value) for key, value in schema.items() if key not in VALUE_CONSTRAINTS}
    if isinstance(schema, list):
        return [_structure_only(item) for item in schema]
    return schema


ANSWER_FORMAT = _structure_only(Answer.model_json_schema())


def chat(messages: list[dict]) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=messages,
        format=ANSWER_FORMAT,
        options={"temperature": 0},
        think=False,
    )
    return response.message.content
