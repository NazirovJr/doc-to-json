"""Поведение пайплайна на пустом входе и плохих ответах модели. LLM подменена, Ollama не нужен."""

import json

from extractor.pipeline import MAX_ATTEMPTS, extract

TEXT = 'ТОО "Ромашка"\nБИН 170340021554\nСчёт на оплату № 7 от 01.02.2026\nВсего к оплате: 1 000 тенге'

ANSWER = {
    "doc_type": "invoice",
    "supplier_name": 'ТОО "Ромашка"',
    "supplier_bin": "170340021554",
    "doc_number": "7",
    "doc_date": "2026-02-01",
    "currency": "KZT",
    "total_amount": 1000,
    "vat_amount": None,
    "line_items": [],
    "field_confidence": {
        "doc_type": 0.9,
        "supplier_name": 0.9,
        "supplier_bin": 0.9,
        "doc_number": 0.9,
        "doc_date": 0.9,
        "currency": 0.9,
        "total_amount": 0.9,
        "vat_amount": 0.9,
        "line_items": 0.9,
    },
    "warnings": [],
}


def answer(**overrides) -> str:
    return json.dumps(ANSWER | overrides)


def test_blank_text_gives_empty_document_without_calling_llm():
    def llm(messages):
        raise AssertionError("модель не должна вызываться")

    doc = extract(" \n\t", llm)

    assert doc.doc_type == "unknown" and doc.line_items == []
    assert len(doc.warnings) == 1


def test_invalid_answer_is_retried_with_validation_error():
    answers = iter([answer(doc_date="01.02.2026", currency="тенге"), answer()])
    prompts = []

    def llm(messages):
        prompts.append(messages[-1]["content"])
        return next(answers)

    doc = extract(TEXT, llm)

    assert doc.currency == "KZT"
    assert "doc_date" in prompts[1] and "currency" in prompts[1]


def test_empty_document_when_every_answer_is_invalid():
    calls = []

    def llm(messages):
        calls.append(messages)
        return "это не JSON"

    doc = extract(TEXT, llm)

    assert len(calls) == MAX_ATTEMPTS
    assert doc.doc_type == "unknown"
    assert doc.supplier_bin is None and doc.total_amount is None and doc.line_items == []
    assert len(doc.warnings) == 1


def test_values_absent_from_text_are_nulled():
    invented = answer(supplier_bin="990140001234", doc_number="A-15", vat_amount=107.14)

    doc = extract(TEXT, lambda messages: invented)

    assert doc.supplier_bin is None and doc.doc_number is None and doc.vat_amount is None
    assert doc.field_confidence.supplier_bin == 0
    assert len(doc.warnings) == 3
    assert doc.total_amount == 1000


def test_ocr_damaged_bin_is_restored_with_warning():
    damaged = "l7O34OO2l554"
    text = TEXT.replace("170340021554", damaged)

    doc = extract(text, lambda messages: answer(supplier_bin=damaged))

    assert doc.supplier_bin == "170340021554"
    assert doc.field_confidence.supplier_bin == 0.5
    assert len(doc.warnings) == 1


def test_unreadable_bin_is_nulled_without_losing_document():
    damaged = "l7O34OO2l55"
    text = TEXT.replace("170340021554", damaged)

    doc = extract(text, lambda messages: answer(supplier_bin=damaged))

    assert doc.supplier_bin is None
    assert doc.total_amount == 1000
    assert len(doc.warnings) == 1
