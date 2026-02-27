import time

import requests

from .config import Settings


class JiraClient:
    def __init__(self, settings: Settings, debug: bool = False) -> None:
        self._settings = settings
        self._debug = debug
        self._session = requests.Session()
        self._session.auth = (settings.JIRA_USER_EMAIL, settings.JIRA_API_TOKEN)
        self._session.headers.update({"Accept": "application/json"})

    def get(self, path: str) -> dict:
        url = f"{self._settings.JIRA_BASE_URL}{path}"
        max_attempts = self._settings.RETRY_MAX_ATTEMPTS
        backoff_base = self._settings.RETRY_BACKOFF_BASE
        backoff_max = self._settings.RETRY_BACKOFF_MAX

        for attempt in range(max_attempts):
            try:
                response = self._session.get(url, timeout=30)

                if self._debug:
                    print(f"[debug] GET {url}")
                    print(f"[debug] status: {response.status_code}")
                    print(f"[debug] response: {response.text[:2000]}")

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    if attempt < max_attempts - 1:
                        sleep_time = min(backoff_base**attempt, backoff_max)
                        time.sleep(sleep_time)
                        continue
                    raise RuntimeError(
                        f"Server error {response.status_code} after {max_attempts} attempts: {url}"
                    )

                if 400 <= response.status_code < 500:
                    raise RuntimeError(
                        f"{response.status_code} Client Error: {response.reason} for url: {url}"
                    )

                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                if attempt < max_attempts - 1:
                    sleep_time = min(backoff_base**attempt, backoff_max)
                    time.sleep(sleep_time)
                    continue
                raise RuntimeError(
                    f"Network error after {max_attempts} attempts: {e}"
                ) from e

        raise RuntimeError(f"Exhausted {max_attempts} retry attempts for: {url}")

    def post(self, path: str, body: dict) -> dict:
        url = f"{self._settings.JIRA_BASE_URL}{path}"
        max_attempts = self._settings.RETRY_MAX_ATTEMPTS
        backoff_base = self._settings.RETRY_BACKOFF_BASE
        backoff_max = self._settings.RETRY_BACKOFF_MAX

        for attempt in range(max_attempts):
            try:
                response = self._session.post(url, json=body, timeout=30)

                if self._debug:
                    print(f"[debug] POST {url}")
                    print(f"[debug] body: {body}")
                    print(f"[debug] status: {response.status_code}")
                    print(f"[debug] response: {response.text[:2000]}")

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    if attempt < max_attempts - 1:
                        sleep_time = min(backoff_base**attempt, backoff_max)
                        time.sleep(sleep_time)
                        continue
                    raise RuntimeError(
                        f"Server error {response.status_code} after {max_attempts} attempts: {url}"
                    )

                # 4xx errors are not retryable
                if 400 <= response.status_code < 500:
                    raise RuntimeError(
                        f"{response.status_code} Client Error: {response.reason} for url: {url}"
                    )

                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                if attempt < max_attempts - 1:
                    sleep_time = min(backoff_base**attempt, backoff_max)
                    time.sleep(sleep_time)
                    continue
                raise RuntimeError(
                    f"Network error after {max_attempts} attempts: {e}"
                ) from e

        raise RuntimeError(f"Exhausted {max_attempts} retry attempts for: {url}")
