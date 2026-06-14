"""Validated API request models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VitalSignsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heart_rate: float | None = Field(default=None, ge=0, le=350)
    systolic_bp: float | None = Field(default=None, ge=0, le=350)
    diastolic_bp: float | None = Field(default=None, ge=0, le=250)
    respiratory_rate: float | None = Field(default=None, ge=0, le=150)
    temperature: float | None = Field(default=None, ge=20, le=50)
    spo2: float | None = Field(default=None, ge=0, le=100)
    gcs: int | None = Field(default=None, ge=3, le=15)
    urine_output_ml_hr: float | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, gt=0, le=700)
    height_cm: float | None = Field(default=None, gt=0, le=300)


class LabResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loinc_code: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=200)
    value: float
    unit: str = Field(min_length=1, max_length=40)
    reference_low: float | None = None
    reference_high: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None
    timestamp: str | None = None


class PatientContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(min_length=1, max_length=128)
    encounter_id: str | None = Field(default=None, max_length=128)
    age: int | None = Field(default=None, ge=0, le=130)
    sex: Literal["M", "F", "other", "unknown"] | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=700)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    vitals: VitalSignsRequest | None = None
    labs: list[LabResultRequest] = Field(default_factory=list, max_length=500)
    medications: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    diagnoses: list[str] = Field(default_factory=list, max_length=200)
    allergies: list[dict[str, str]] = Field(default_factory=list, max_length=200)
    location: str | None = Field(default=None, max_length=100)


class CDSSRequest(BaseModel):
    hook: Literal[
        "patient-view",
        "order-select",
        "order-sign",
        "appointment-book",
        "encounter-start",
        "encounter-discharge",
    ] = "patient-view"
    context: PatientContextRequest


class CDSHooksRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    hook: str
    hookInstance: str
    context: dict[str, Any]
    prefetch: dict[str, Any] = Field(default_factory=dict)
