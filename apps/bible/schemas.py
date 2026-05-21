"""Pydantic schemas used by the bible app's HTTP handlers."""

from typing import Annotated, Any, Literal, Union

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


class _TextCriterion(BaseModel):
    type: Literal["text"]
    value: str = Field(min_length=1)


class _EnglishCriterion(BaseModel):
    type: Literal["english"]
    value: str = Field(min_length=1)


class _HebrewCriterion(BaseModel):
    type: Literal["hebrew"]
    value: str = Field(min_length=1)
    concordance_id: str = Field(min_length=1)


class _GreekCriterion(BaseModel):
    type: Literal["greek"]
    value: str = Field(min_length=1)
    concordance_id: str = Field(min_length=1)


class _AuthorCriterion(BaseModel):
    type: Literal["author"]
    value: str = Field(min_length=1)


class _SpeakerCriterion(BaseModel):
    type: Literal["speaker"]
    value: str = Field(min_length=1)


class _BookCriterion(BaseModel):
    type: Literal["book"]
    value: str

    @field_validator("value")
    @classmethod
    def _resolve(cls, value):
        code = datasets.resolve_book(value)
        if code is None:
            raise ValueError(f"unknown book: {value}")
        return code


class _TestamentCriterion(BaseModel):
    type: Literal["testament"]
    value: Literal["old", "new"]


SearchCriterion = Annotated[
    Union[
        _TextCriterion,
        _EnglishCriterion,
        _HebrewCriterion,
        _GreekCriterion,
        _AuthorCriterion,
        _SpeakerCriterion,
        _BookCriterion,
        _TestamentCriterion,
    ],
    Field(discriminator="type"),
]


class SearchRequest(BaseModel):
    """JSON body for the search endpoint: a non-empty list of criteria AND'd together."""

    criteria: list[SearchCriterion] = Field(min_length=1)


class SearchPageQuery(BaseModel):
    """Pagination params for the search endpoint."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)


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
