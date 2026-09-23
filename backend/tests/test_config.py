import pytest
from pathlib import Path
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def test_missing_required_env_vars_fails_validation():
    """Ensure missing required variables raise ValidationError during Settings loading."""
    dummy_env = Path("dummy_empty_test.env")
    dummy_env.write_text("")

    class TestSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=str(dummy_env), extra="ignore")
        DATABASE_URL: str
        REDIS_URL: str

    try:
        with pytest.raises(ValidationError):
            TestSettings()
    finally:
        if dummy_env.exists():
            dummy_env.unlink()
