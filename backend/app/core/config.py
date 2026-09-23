import sys
from pathlib import Path
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Locate .env file (check backend/.env or root .env)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent

if (_BACKEND_DIR / ".env").is_file():
    ENV_PATH = _BACKEND_DIR / ".env"
elif (_ROOT_DIR / ".env").is_file():
    ENV_PATH = _ROOT_DIR / ".env"
else:
    ENV_PATH = None

# 2. Stop system boot if .env file is missing
if not ENV_PATH or not ENV_PATH.is_file():
    print(
        "\n[SYSTEM BOOT ERROR] Halting startup: Missing .env file!\n"
        "Please create a .env file from .env.example before starting the server.\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


# 3. Settings definition with required variables
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Enterprise AI Platform"
    PROJECT_NAME: str = "Enterprise AI Platform"
    APP_ENV: str = "development"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Required variables - boot stops if missing in .env
    DATABASE_URL: str = Field(..., description="Postgres connection string")
    REDIS_URL: str = Field(..., description="Redis connection string")
    POSTGRES_DB: str = Field(default="app_db", description="Postgres Database Name")


# 4. Initialize and validate settings immediately
try:
    settings = Settings()
except ValidationError as exc:
    print(
        "\n[SYSTEM BOOT ERROR] Halting startup: Missing required environment variables:\n",
        file=sys.stderr,
    )
    for err in exc.errors():
        field_name = err["loc"][0] if err["loc"] else "unknown"
        print(f"  - {field_name}: {err['msg']}", file=sys.stderr)
    print("\nPlease verify your .env file matches requirements.\n", file=sys.stderr)
    raise SystemExit(1)
