"""Configuration and settings validation tests."""

import pytest
from pydantic import ValidationError

from app.core.config import DEV_SECRET_KEYS, Settings


def test_dev_default_secret_is_accepted_outside_production() -> None:
    settings = Settings(_env_file=None)
    assert settings.environment != "production"
    assert settings.secret_key in DEV_SECRET_KEYS


@pytest.mark.parametrize("placeholder", sorted(DEV_SECRET_KEYS))
def test_production_refuses_placeholder_secrets(placeholder: str) -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, environment="production", secret_key=placeholder)


def test_production_accepts_a_real_secret() -> None:
    real_secret = "an-actually-unique-value"  # noqa: S105
    settings = Settings(_env_file=None, environment="production", secret_key=real_secret)  # noqa: S106
    assert settings.secret_key == real_secret
