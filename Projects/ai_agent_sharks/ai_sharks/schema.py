from typing import Literal, Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_PITCH_CHARS = 12_000


def validate_pitch(pitch: str) -> str:
    if not isinstance(pitch, str) or not pitch.strip():
        raise ValueError("Enter a startup pitch before running the panel.")
    pitch = pitch.strip()
    if len(pitch) > MAX_PITCH_CHARS:
        raise ValueError(f"Keep the pitch within {MAX_PITCH_CHARS:,} characters.")
    return pitch





class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    shark: str = Field(description="Exact investor name supplied in the instructions")
    stance: Literal["INVEST", "PASS"]
    # Required-but-nullable is intentional: strict JSON schemas require all keys.
    offer: str | None = Field(description="A concrete investment offer, or null for PASS")
    reasoning: str = Field(description="Two or three sentences in the investor's voice")

    @field_validator("shark", "reasoning", "offer")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Text fields must not be blank.")
        return value

    @model_validator(mode="after")
    def check_offer(self) -> Self:
        if self.stance == "INVEST" and self.offer is None:
            raise ValueError("INVEST requires an offer.")
        if self.stance == "PASS" and self.offer is not None:
            raise ValueError("PASS must have a null offer.")
        return self

