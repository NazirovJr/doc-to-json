from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1)]
Amount = Annotated[float, Field(ge=0)]
Confidence = Annotated[float, Field(ge=0, le=1)]


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class LineItem(Strict):
    name: Text
    qty: Amount | None
    price: Amount | None


class FieldConfidence(Strict):
    doc_type: Confidence
    supplier_name: Confidence
    supplier_bin: Confidence
    doc_number: Confidence
    doc_date: Confidence
    currency: Confidence
    total_amount: Confidence
    vat_amount: Confidence
    line_items: Confidence


class Document(Strict):
    doc_type: Literal["invoice", "commercial_offer", "act", "unknown"]
    supplier_name: Text | None
    supplier_bin: Annotated[str, Field(pattern=r"^[0-9]{12}$")] | None
    doc_number: Text | None
    doc_date: date | None
    currency: Literal["KZT", "USD", "EUR"] | None
    total_amount: Amount | None
    vat_amount: Amount | None
    line_items: list[LineItem]
    field_confidence: FieldConfidence
    warnings: list[str]

    @classmethod
    def empty(cls, warning: str) -> "Document":
        """Валидный документ без данных — результат, когда извлекать нечего или модели доверять нельзя."""
        scalars = dict.fromkeys(
            ("supplier_name", "supplier_bin", "doc_number", "doc_date", "currency", "total_amount", "vat_amount")
        )
        confidence = FieldConfidence(**dict.fromkeys(FieldConfidence.model_fields, 0.0))
        return cls(doc_type="unknown", **scalars, line_items=[], field_confidence=confidence, warnings=[warning])


class Answer(Document):
    """Ответ модели: БИН переписан из документа как есть, к 12 цифрам его приводит сверка с текстом."""

    supplier_bin: Text | None
