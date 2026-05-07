"""
qaforge.core.config_loader
==========================
Loads YAML config for the active environment, merges environment variables,
and exposes a typed `Config` Pydantic model used throughout the framework.

Env selection precedence:
    1. behave userdata `-D env=staging`
    2. environment variable QAFORGE_ENV
    3. default 'dev'
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = ROOT / "config" / "environments"

load_dotenv(ROOT / ".env", override=False)


# ------------- Pydantic schema (typed config) ---------------
class UIConfig(BaseModel):
    base_url: str
    default_timeout_ms: int = 30000
    navigation_timeout_ms: int = 45000
    viewport: Dict[str, int] = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    locale: str = "en-US"
    timezone: str = "UTC"
    record_video: bool = True
    trace: str = "retain-on-failure"
    screenshot_on_failure: bool = True
    slow_mo_ms: int = 0


class RestConfig(BaseModel):
    base_url: str
    timeout_seconds: int = 30


class GraphQLConfig(BaseModel):
    endpoint: str


class GrpcConfig(BaseModel):
    host: str
    port: int
    use_tls: bool = True


class WSConfig(BaseModel):
    url: str


class AsyncAPIConfig(BaseModel):
    kafka_brokers: List[str] = Field(default_factory=list)


class APIConfig(BaseModel):
    rest: RestConfig
    graphql: GraphQLConfig
    grpc: GrpcConfig
    websocket: WSConfig
    async_api: AsyncAPIConfig


class OAuthConfig(BaseModel):
    token_url: str
    client_id_env: str
    client_secret_env: str
    scope: str = ""


class PasswordOTPConfig(BaseModel):
    login_url: str
    otp_url: str


class AuthConfig(BaseModel):
    oauth: OAuthConfig
    password_otp: PasswordOTPConfig


class DBSpec(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    db: Optional[str] = None
    user_env: Optional[str] = None
    password_env: Optional[str] = None
    uri_env: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None


class DatabasesConfig(BaseModel):
    postgres: DBSpec
    mysql: DBSpec
    mongo: DBSpec
    dynamo: DBSpec


class AIConfig(BaseModel):
    llm_provider: str
    llm_model: str
    api_key_env: str
    rag_corpus_path: str
    thresholds: Dict[str, float] = Field(default_factory=dict)


class Config(BaseModel):
    environment: str
    ui: UIConfig
    api: APIConfig
    auth: AuthConfig
    databases: DatabasesConfig
    ai: AIConfig
    read_only: bool = False


# ------------- Loader ---------------
def _resolve_env_name(behave_userdata: Optional[Dict[str, Any]] = None) -> str:
    if behave_userdata and behave_userdata.get("env"):
        return str(behave_userdata["env"])
    return os.environ.get("QAFORGE_ENV", "dev")


@lru_cache(maxsize=8)
def _load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_config(behave_userdata: Optional[Dict[str, Any]] = None) -> Config:
    """Load and validate config for the active environment."""
    env = _resolve_env_name(behave_userdata)
    yaml_path = CONFIG_DIR / f"{env}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Environment config not found: {yaml_path}. "
            f"Available: {[p.stem for p in CONFIG_DIR.glob('*.yaml')]}"
        )
    raw = _load_yaml(str(yaml_path))
    return Config(**raw)


def secret(env_var: str, default: Optional[str] = None) -> str:
    """Resolve a secret from environment variable, raising if missing and no default."""
    val = os.environ.get(env_var, default)
    if val is None:
        raise EnvironmentError(f"Required secret env var not set: {env_var}")
    return val
