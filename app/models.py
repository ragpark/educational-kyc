from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import registry

mapper_registry = registry()

@mapper_registry.mapped
@dataclass
class UserAccount:
    __tablename__ = "user_accounts"
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(init=False, metadata={"sa": Column(Integer, primary_key=True)})
    username: str = field(metadata={"sa": Column(String(100), unique=True, nullable=False)})
    hashed_password: str = field(metadata={"sa": Column(String(200), nullable=False)})
    role: str = field(default="user", metadata={"sa": Column(String(50), nullable=False)})


@mapper_registry.mapped
@dataclass
class ProviderApplication:
    __tablename__ = "applications"
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(init=False, metadata={"sa": Column(Integer, primary_key=True)})
    verification_id: str = field(metadata={"sa": Column(String(36), unique=True, nullable=False)})
    organisation_name: str = field(metadata={"sa": Column(String(255), nullable=False)})
    trading_name: str | None = field(default=None, metadata={"sa": Column(String(255))})
    provider_type: str = field(default="Training Provider", metadata={"sa": Column(String(100))})
    company_number: str | None = field(default=None, metadata={"sa": Column(String(20))})
    urn: str | None = field(default=None, metadata={"sa": Column(String(20))})
    ukprn: str | None = field(default=None, metadata={"sa": Column(String(20))})
    jcq_centre_number: str | None = field(default=None, metadata={"sa": Column(String(20))})
    postcode: str | None = field(default=None, metadata={"sa": Column(String(20))})
    contact_email: str | None = field(default=None, metadata={"sa": Column(String(255))})
    status: str = field(default="processing", metadata={"sa": Column(String(50))})
    risk_level: str = field(default="unknown", metadata={"sa": Column(String(50))})
    created_at: datetime = field(default_factory=datetime.utcnow, metadata={"sa": Column(DateTime, default=datetime.utcnow)})
    kyc_results: dict = field(default_factory=dict, metadata={"sa": Column(JSON, default={})})
    processing_started: datetime | None = field(default_factory=datetime.utcnow, metadata={"sa": Column(DateTime)})
    processing_completed: datetime | None = field(default=None, metadata={"sa": Column(DateTime)})

