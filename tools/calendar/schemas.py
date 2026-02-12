from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class EventDateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dateTime: str | None = None
    date: str | None = None
    timeZone: str | None = None

    @model_validator(mode="after")
    def validate_date_spec(self) -> "EventDateSpec":
        has_date_time = bool(self.dateTime)
        has_date = bool(self.date)
        if has_date_time == has_date:
            raise ValueError("Provide exactly one of dateTime or date.")
        return self


class EventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: EventDateSpec
    end: EventDateSpec
    attendees: list[dict[str, Any]] | None = None
    reminders: dict[str, Any] | None = None
    transparency: str | None = None


class EventUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: EventDateSpec | None = None
    end: EventDateSpec | None = None
    attendees: list[dict[str, Any]] | None = None
    reminders: dict[str, Any] | None = None
    transparency: str | None = None

    @model_validator(mode="after")
    def validate_non_empty_patch(self) -> "EventUpdateRequest":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one field must be provided for update.")
        return self
