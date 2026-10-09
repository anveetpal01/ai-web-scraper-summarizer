"""Request and response models for the API."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class SummarizeRequest(BaseModel):
    url: str = Field(
        description="The web page to summarize. https:// is added if the scheme is missing.",
        examples=["https://en.wikipedia.org/wiki/Web_scraping"],
    )


class SummarizeResponse(BaseModel):
    # Python code uses snake_case, the JSON sent to the frontend uses camelCase.
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)

    url: str
    title: str
    summary: str
    key_points: list[str]
    word_count: int
    truncated: bool


class ErrorResponse(BaseModel):
    error: str
