"""Central configuration (12-factor, read from environment / repo-root .env)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # LLM (Azure AI Foundry, OpenAI-compatible v1 endpoint, Bearer key)
    azure_endpoint_url: str = ""          # e.g. https://<account>.services.ai.azure.com/openai/v1
    azure_api_key: str = ""
    llm_model: str = "gpt-5-4-mini"
    llm_mode: str = "auto"                # auto | live | fake  (auto = live if key set, else fake)

    # Paths
    raw_data_dir: Path = REPO_ROOT / "docs"
    knowledge_dir: Path = REPO_ROOT / "knowledge"
    var_dir: Path = REPO_ROOT / "var"
    db_url: str = ""

    @property
    def database_url(self) -> str:
        return self.db_url or f"sqlite:///{self.var_dir / 'app.db'}"

    @property
    def llm_live(self) -> bool:
        if self.llm_mode == "fake":
            return False
        return bool(self.azure_api_key and self.azure_endpoint_url)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.var_dir.mkdir(parents=True, exist_ok=True)
    return s
