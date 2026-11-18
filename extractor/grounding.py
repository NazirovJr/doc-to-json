"""Сверка ответа модели с исходным текстом: значение, которого в документе нет, обнуляется."""

import re

from .schema import Answer, Document

# Символы, которые OCR путает с цифрами: латинская и кириллическая «о», l, I, |.
OCR_DIGITS = str.maketrans("oоli|", "00111")


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def ground(answer: Answer, text: str) -> Document:
    source = _squash(text)
    restored = source.translate(OCR_DIGITS)
    confidence = answer.field_confidence

    def drop(field: str) -> None:
        setattr(answer, field, None)
        setattr(confidence, field, 0.0)
        answer.warnings.append(f"{field}: значение не найдено в тексте в читаемом виде, поле обнулено")

    def mark_restored(field: str) -> None:
        setattr(confidence, field, min(getattr(confidence, field), 0.5))
        answer.warnings.append(f"{field}: восстановлено после ошибок OCR, требует проверки")

    if answer.supplier_bin is not None:
        bin_ = _squash(answer.supplier_bin).translate(OCR_DIGITS)
        if re.fullmatch(r"[0-9]{12}", bin_) and bin_ in restored:
            answer.supplier_bin = bin_
            if bin_ not in source:
                mark_restored("supplier_bin")
        else:
            drop("supplier_bin")

    if answer.doc_number is not None:
        number = _squash(answer.doc_number)
        if number.translate(OCR_DIGITS) not in restored:
            drop("doc_number")
        elif number not in source:
            mark_restored("doc_number")

    # Сумма НДС должна стоять в тексте цифрами: посчитанную моделью не принимаем.
    if answer.vat_amount is not None and _digits(f"{answer.vat_amount:.2f}".rstrip("0")) not in _digits(text):
        drop("vat_amount")

    return Document.model_validate(answer.model_dump())
