import json
from pathlib import Path

from .config import Settings


class OutputWriter:
    def __init__(self, settings: Settings, run_id: str) -> None:
        self._output_dir = Path(settings.OUTPUT_DIR)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._issues_per_file = settings.OUTPUT_ISSUES_PER_FILE
        self._run_id = run_id
        self._buffer: list = []
        self._file_index = 1

    def add_issues(self, issues: list) -> None:
        self._buffer.extend(issues)
        while len(self._buffer) >= self._issues_per_file:
            batch = self._buffer[: self._issues_per_file]
            self._buffer = self._buffer[self._issues_per_file :]
            self._write_batch(batch)

    def flush(self) -> None:
        if self._buffer:
            self._write_batch(self._buffer)
            self._buffer = []

    def _write_batch(self, batch: list) -> None:
        path = self._output_dir / f"{self._run_id}-{self._file_index}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)
        self._file_index += 1
