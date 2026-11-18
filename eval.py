"""Прогон тестового набора data/*.txt против эталонов data/*.json: python eval.py"""

import re
import sys
from collections import Counter
from pathlib import Path

from extractor.llm import MODEL
from extractor.pipeline import extract
from extractor.schema import Document, FieldConfidence

DATA = Path(__file__).parent / "data"
FIELDS = list(FieldConfidence.model_fields)
WARNINGS = "warnings"


def comparable(doc: Document) -> dict:
    """Поля данных плюс warnings, сведённые к факту наличия: текст предупреждений не сравнить."""
    values = doc.model_dump(include=set(FIELDS))
    return values | {WARNINGS: True if doc.warnings else None}


def normalize(value):
    if isinstance(value, str):
        return re.sub(r"[\s\"'«»“”„]", "", value).lower()
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def is_empty(value) -> bool:
    return value is None or value == []


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    stats = {field: Counter() for field in [*FIELDS, WARNINGS]}
    mismatches = []
    paths = sorted(DATA.glob("*.txt"))

    for path in paths:
        expected = comparable(Document.model_validate_json(path.with_suffix(".json").read_text(encoding="utf-8")))
        actual = comparable(extract(path.read_text(encoding="utf-8")))
        for field, counter in stats.items():
            want, got = expected[field], actual[field]
            if normalize(got) == normalize(want):
                counter["correct"] += 1
                continue
            counter["hallucinated"] += is_empty(want) and not is_empty(got)
            counter["missed"] += is_empty(got) and not is_empty(want)
            mismatches.append(f"  {path.stem} / {field}: ожидалось {want!r}, получено {got!r}")
        print(f"обработан {path.stem}", flush=True)

    def row(name: str, counter: Counter, total: int) -> str:
        accuracy = f"{counter['correct']}/{total}"
        return f"{name:<16}{accuracy:>8}{counter['hallucinated']:>14}{counter['missed']:>10}"

    print(f"\nДокументов: {len(paths)}, модель: {MODEL}\n")
    print(f"{'Поле':<16}{'Точность':>8}{'Галлюцинации':>14}{'Пропуски':>10}")
    for field in FIELDS:
        print(row(field, stats[field], len(paths)))
    print(row("ИТОГО", sum((stats[field] for field in FIELDS), Counter()), len(paths) * len(FIELDS)))
    print(row("warnings*", stats[WARNINGS], len(paths)))
    print("* сравнивается только наличие предупреждений; в ИТОГО не входит")
    if mismatches:
        print("\nРасхождения:", *mismatches, sep="\n")


if __name__ == "__main__":
    main()
