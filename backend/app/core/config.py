"""Application configuration and settings.

Centralises all privacy, retention, security and data-residency settings so they
can be enforced consistently across the codebase (see requirements doc:
Privacy, Consent, Retention, RBAC & Audit).
"""
from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

_DIR = Path(__file__).resolve().parent.parent.parent.parent
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment / .env.

    Sensitive values (secret keys, encryption keys) MUST be provided via the
    environment and never committed to source control.
    """

    model_config = SettingsConfigDict(env_file=_DIR / ".env", env_prefix="MHC_", extra="ignore")

    # --- Application ---
    app_name: str = "Mental Health Screening App"
    environment: Literal["dev", "staging", "prod"] = "dev"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/mhcare"
    )

    # --- Authentication ---
    jwt_secret: str = Field(default="CHANGE_ME_IN_PROD")
    jwt_algorithm: str = "HS256"
    access_token_ttl: timedelta = timedelta(minutes=30)
    refresh_token_ttl: timedelta = timedelta(days=7)
    bcrypt_schemes: str = "bcrypt"

    # --- Field-level encryption (sensitive health data) ---
    # 32 url-safe base64 bytes produced by cryptography.fernet.Fernet.generate_key()
    field_encryption_key: str = Field(default="CHANGE_ME_ENCRYPTION_KEY")

    # --- Privacy / data residency ---
    # Requirement: data stored in India, or clearly disclosed if transferred.
    data_residency_region: str = "in"  # ISO-3166 country code for India
    data_transfer_disclosed: bool = False  # set True only if a lawful transfer is documented

    # --- Consent ---
    consent_text_version: str = "2024-08-01"
    research_consent_text_version: str = "2024-08-01"

    # --- Retention (Requirement 3) ---
    # Identifiable data kept while active + a maximum grace window after inactivity.
    identifiable_retention_years: int = 5  # within the 3-5 year range
    inactive_grace_days: int = 365
    # High-risk cases (e.g. positive C-SSRS) may follow a longer clinical retention.
    high_risk_retention_years: int = 7
    audit_log_retention_years: int = 3  # within the 2-3 year requirement

    # --- RBAC default role for self-registered users ---
    default_role: str = "patient"

    # --- Security headers / CORS ---
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"

    def validate_secrets(self) -> None:
        """Validate or auto-generate secrets.

        In dev mode, placeholder values are replaced with auto-generated secrets
        and a warning is printed.  In staging/prod the app refuses to start with
        placeholder secrets.
        """
        _placeholder_jwt = ("CHANGE_ME_IN_PROD", "replace-with-long-random-string", "")
        _placeholder_enc = ("CHANGE_ME_ENCRYPTION_KEY", "replace-with-fernet-key", "")

        if self.environment == "dev":
            if self.jwt_secret in _placeholder_jwt:
                self.jwt_secret = secrets.token_urlsafe(32)
                print("[WARN] MHC_JWT_SECRET was a placeholder — auto-generated for this session. "
                      "Set a real value in .env for persistence.")
            if self.field_encryption_key in _placeholder_enc:
                from cryptography.fernet import Fernet
                self.field_encryption_key = Fernet.generate_key().decode()
                print("[WARN] MHC_FIELD_ENCRYPTION_KEY was a placeholder — auto-generated for this session. "
                      "Set a real value in .env for persistence.")
        else:
            errors: list[str] = []
            if self.jwt_secret in _placeholder_jwt:
                errors.append("MHC_JWT_SECRET is not set. Generate one: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
            if self.field_encryption_key in _placeholder_enc:
                errors.append("MHC_FIELD_ENCRYPTION_KEY is not set. Generate one: cd backend && python -c \"from app.security.encryption import generate_key; print(generate_key())\"")
            if errors:
                raise SystemExit("\n".join(["Startup failed:"] + errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
