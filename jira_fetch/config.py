from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    JIRA_BASE_URL: str
    JIRA_USER_EMAIL: str
    JIRA_API_TOKEN: str

    JIRA_MAX_RESULTS_PER_PAGE: int = 100
    OUTPUT_ISSUES_PER_FILE: int = 250
    OUTPUT_DIR: str = "./output"
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_BASE: float = 2.0
    RETRY_BACKOFF_MAX: float = 60.0
    REQUEST_DELAY_SECONDS: float = 0.5
    INCLUDE_WORKLOGS: bool = False
    INCLUDE_CHANGELOGS: bool = False

    @field_validator("JIRA_BASE_URL")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")
