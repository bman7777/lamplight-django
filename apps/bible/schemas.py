"""Pydantic schemas used by the bible app's HTTP handlers."""

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .utilities import datasets


class VersesQuery(BaseModel):
    """Validated path + query params for the verses endpoint.

    `book` is normalized to its short code; `chapter` and `verse` are either
    a positive int or the wildcard string '*'.
    """

    book: str
    chapter: Union[Literal["*"], int]
    verse: Union[Literal["*"], int]
    dataset: Literal["bible", "faves", "OT", "NT"] = "bible"
    order: Literal["canonical", "random"] = "canonical"
    version: Literal["nasb95"] = "nasb95"
    limit: int = Field(default=25, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    seed: Union[int, None] = Field(default=None, ge=0, le=2**31 - 1)

    @field_validator("book")
    @classmethod
    def _resolve_book(cls, value):
        code = datasets.resolve_book(value)
        if code is None:
            raise ValueError(f"unknown book: {value}")
        return code

    @field_validator("chapter", "verse", mode="before")
    @classmethod
    def _parse_int_or_wildcard(cls, value):
        if value == "*":
            return "*"
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("must be '*' or a positive integer") from exc
        if parsed < 1:
            raise ValueError("must be '*' or a positive integer")
        return parsed


class ConcordanceEntryResponse(BaseModel):
    """Serialized shape of a ConcordanceEntry returned by the concordance view."""

    model_config = ConfigDict(from_attributes=True)

    concord_id: str
    original_word: str
    transliteration: str
    part_of_speech: str
    english_translations: list[Any]
    outline_definitions: list[Any]
    strongs_definition: list[Any]
