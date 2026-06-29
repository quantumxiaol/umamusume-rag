from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ..config import config

DEFAULT_FILE_GLOBS = ("*.md", "*.txt", "*.csv")
ALLOWED_GLOB_SUFFIXES = (".md", ".txt", ".csv")
MAX_QUERY_CHARS = 200
MAX_GLOBS = 8
MAX_RESULTS = 200
MAX_CONTEXT_LINES = 8
MAX_QUERIES = 12


class GrepPolicyError(ValueError):
    """Raised when a search request violates the grep safety policy."""


@dataclass(frozen=True)
class GrepSearchResult:
    id: int
    file: str
    line_number: int
    column: int | None
    line: str
    context: str
    submatches: list[dict[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RipgrepSearcher:
    """A narrow ripgrep wrapper for MCP tools.

    The caller can only pass search terms and constrained options. Commands are
    always executed with an argv list, fixed-string matching, and a fixed root.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        rg_path: str | None = None,
        timeout_seconds: float = 20.0,
        max_filesize: str = "10M",
    ):
        self.root = self._resolve_root(root or config.RAG_DIRECTORY)
        self.rg_path = rg_path or shutil.which("rg")
        self.timeout_seconds = timeout_seconds
        self.max_filesize = max_filesize
        if not self.rg_path:
            raise RuntimeError("ripgrep executable not found. Install it with: brew install ripgrep")

    def search(
        self,
        query: str,
        *,
        max_results: int = 20,
        context_lines: int = 2,
        file_globs: Iterable[str] | str | None = None,
        ignore_case: bool = False,
    ) -> dict[str, Any]:
        started_at = time.monotonic()
        query = self._validate_query(query)
        max_results = self._clamp_int(max_results, minimum=0, maximum=MAX_RESULTS)
        context_lines = self._clamp_int(context_lines, minimum=0, maximum=MAX_CONTEXT_LINES)
        globs = self._validate_globs(file_globs)

        total_matches, files_with_matches = self._count_matches(
            query=query,
            globs=globs,
            ignore_case=ignore_case,
        )
        if total_matches == 0 or max_results == 0:
            return {
                "status": "success",
                "query": query,
                "searched_directory": str(self.root),
                "file_globs": list(globs),
                "ignore_case": ignore_case,
                "match_count": total_matches,
                "returned_count": 0,
                "files_with_matches": files_with_matches,
                "truncated": total_matches > 0,
                "elapsed_seconds": round(time.monotonic() - started_at, 4),
                "results": [],
            }

        cmd = self._build_command(
            query=query,
            globs=globs,
            ignore_case=ignore_case,
            max_count_per_file=max(1, min(max_results, 50)),
        )
        completed = subprocess.run(
            cmd,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode not in (0, 1):
            return {
                "status": "error",
                "query": query,
                "message": self._trim_error(completed.stderr),
                "searched_directory": str(self.root),
            }

        results = self._parse_results(
            completed.stdout,
            max_results=max_results,
            context_lines=context_lines,
        )
        return {
            "status": "success",
            "query": query,
            "searched_directory": str(self.root),
            "file_globs": list(globs),
            "ignore_case": ignore_case,
            "match_count": total_matches,
            "returned_count": len(results),
            "files_with_matches": files_with_matches,
            "truncated": total_matches > len(results),
            "elapsed_seconds": round(time.monotonic() - started_at, 4),
            "results": [result.to_dict() for result in results],
        }

    def search_many(
        self,
        queries: Iterable[str],
        *,
        max_results_per_query: int = 10,
        context_lines: int = 2,
        file_globs: Iterable[str] | str | None = None,
        ignore_case: bool = False,
    ) -> dict[str, Any]:
        query_list = list(queries)
        if not query_list:
            raise GrepPolicyError("queries must not be empty")
        if len(query_list) > MAX_QUERIES:
            raise GrepPolicyError(f"too many queries; maximum is {MAX_QUERIES}")

        started_at = time.monotonic()
        per_query = []
        total_matches = 0
        total_returned = 0
        file_match_count_sum = 0

        for query in query_list:
            result = self.search(
                query,
                max_results=max_results_per_query,
                context_lines=context_lines,
                file_globs=file_globs,
                ignore_case=ignore_case,
            )
            per_query.append(result)
            if result.get("status") == "success":
                total_matches += int(result.get("match_count", 0))
                total_returned += int(result.get("returned_count", 0))
                file_match_count_sum += int(result.get("files_with_matches", 0))

        return {
            "status": "success",
            "query_count": len(query_list),
            "match_count": total_matches,
            "returned_count": total_returned,
            "file_match_count_sum": file_match_count_sum,
            "elapsed_seconds": round(time.monotonic() - started_at, 4),
            "results": per_query,
        }

    def _build_command(
        self,
        *,
        query: str,
        globs: tuple[str, ...],
        ignore_case: bool,
        max_count_per_file: int,
    ) -> list[str]:
        cmd = [
            self.rg_path,
            "--json",
            "--fixed-strings",
            "--line-number",
            "--column",
            "--with-filename",
            "--color",
            "never",
            "--max-filesize",
            self.max_filesize,
            "--max-count",
            str(max_count_per_file),
        ]
        if ignore_case:
            cmd.append("--ignore-case")
        for file_glob in globs:
            cmd.extend(["--glob", file_glob])
        cmd.extend(["--", query, "."])
        return cmd

    def _build_count_command(
        self,
        *,
        query: str,
        globs: tuple[str, ...],
        ignore_case: bool,
    ) -> list[str]:
        cmd = [
            self.rg_path,
            "--count-matches",
            "--fixed-strings",
            "--with-filename",
            "--color",
            "never",
            "--max-filesize",
            self.max_filesize,
        ]
        if ignore_case:
            cmd.append("--ignore-case")
        for file_glob in globs:
            cmd.extend(["--glob", file_glob])
        cmd.extend(["--", query, "."])
        return cmd

    def _count_matches(
        self,
        *,
        query: str,
        globs: tuple[str, ...],
        ignore_case: bool,
    ) -> tuple[int, int]:
        completed = subprocess.run(
            self._build_count_command(query=query, globs=globs, ignore_case=ignore_case),
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode == 1:
            return 0, 0
        if completed.returncode != 0:
            raise RuntimeError(self._trim_error(completed.stderr))

        total_matches = 0
        files_with_matches = 0
        for line in completed.stdout.splitlines():
            if not line:
                continue
            try:
                _, count_text = line.rsplit(":", 1)
                count = int(count_text)
            except ValueError:
                continue
            if count > 0:
                files_with_matches += 1
                total_matches += count
        return total_matches, files_with_matches

    def _parse_results(
        self,
        output: str,
        *,
        max_results: int,
        context_lines: int,
    ) -> list[GrepSearchResult]:
        results: list[GrepSearchResult] = []
        line_cache: dict[Path, list[str]] = {}

        for raw_line in output.splitlines():
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "match":
                continue

            data = event.get("data", {})
            path_text = data.get("path", {}).get("text", "")
            file_path = self._resolve_result_path(path_text)
            if file_path is None:
                continue

            relative_file = file_path.relative_to(self.root).as_posix()
            if len(results) >= max_results:
                continue

            line_number = int(data.get("line_number", 0))
            line_text = data.get("lines", {}).get("text", "").rstrip("\n")
            submatches = []
            for item in data.get("submatches", []):
                submatches.append(
                    {
                        "start": int(item.get("start", 0)),
                        "end": int(item.get("end", 0)),
                    }
                )
            results.append(
                GrepSearchResult(
                    id=len(results) + 1,
                    file=relative_file,
                    line_number=line_number,
                    column=self._first_column(data),
                    line=line_text,
                    context=self._read_context(
                        file_path,
                        line_number=line_number,
                        context_lines=context_lines,
                        cache=line_cache,
                    ),
                    submatches=submatches,
                )
            )
        return results

    def _read_context(
        self,
        file_path: Path,
        *,
        line_number: int,
        context_lines: int,
        cache: dict[Path, list[str]],
    ) -> str:
        if context_lines <= 0:
            return ""
        if file_path not in cache:
            try:
                cache[file_path] = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                cache[file_path] = []
        lines = cache[file_path]
        if not lines or line_number <= 0:
            return ""

        start = max(1, line_number - context_lines)
        end = min(len(lines), line_number + context_lines)
        return "\n".join(f"{idx}: {lines[idx - 1]}" for idx in range(start, end + 1))

    def _resolve_result_path(self, path_text: str) -> Path | None:
        if not path_text:
            return None
        path = Path(path_text)
        resolved = path.resolve() if path.is_absolute() else (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            return None
        return resolved

    def _resolve_root(self, root: str | Path) -> Path:
        resolved = Path(root).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"grep root does not exist: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"grep root is not a directory: {resolved}")
        return resolved

    def _validate_query(self, query: str) -> str:
        if not isinstance(query, str):
            raise GrepPolicyError("query must be a string")
        value = query.strip()
        if not value:
            raise GrepPolicyError("query must not be empty")
        if len(value) > MAX_QUERY_CHARS:
            raise GrepPolicyError(f"query is too long; maximum is {MAX_QUERY_CHARS} characters")
        if "\x00" in value or "\n" in value or "\r" in value:
            raise GrepPolicyError("query must be a single-line string")
        return value

    def _validate_globs(self, file_globs: Iterable[str] | str | None) -> tuple[str, ...]:
        if not file_globs:
            return DEFAULT_FILE_GLOBS
        if isinstance(file_globs, str):
            raw_globs = [item.strip() for item in file_globs.split(",")]
        else:
            raw_globs = [str(item).strip() for item in file_globs]

        globs = [item for item in raw_globs if item]
        if not globs:
            return DEFAULT_FILE_GLOBS
        if len(globs) > MAX_GLOBS:
            raise GrepPolicyError(f"too many file globs; maximum is {MAX_GLOBS}")

        validated = []
        for file_glob in globs:
            if len(file_glob) > 80:
                raise GrepPolicyError("file glob is too long")
            if file_glob.startswith("/") or "\\" in file_glob:
                raise GrepPolicyError("file glob must be a relative POSIX-style pattern")
            parts = Path(file_glob).parts
            if ".." in parts:
                raise GrepPolicyError("file glob must not contain '..'")
            if any(char in file_glob for char in ("\x00", "\n", "\r")):
                raise GrepPolicyError("file glob must be a single-line string")
            if not file_glob.endswith(ALLOWED_GLOB_SUFFIXES):
                raise GrepPolicyError(
                    "file glob must target one of these suffixes: "
                    + ", ".join(ALLOWED_GLOB_SUFFIXES)
                )
            validated.append(file_glob)
        return tuple(validated)

    def _clamp_int(self, value: int, *, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise GrepPolicyError("numeric option must be an integer")
        return max(minimum, min(number, maximum))

    def _first_column(self, data: dict[str, Any]) -> int | None:
        submatches = data.get("submatches", [])
        if not submatches:
            return None
        return int(submatches[0].get("start", 0)) + 1

    def _trim_error(self, stderr: str) -> str:
        message = stderr.strip()
        if not message:
            return "ripgrep failed"
        return message[:500]
