from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..config import config

CHARACTER_INDEX_FILE = "umamusume_character_baseinfo.csv"
PLOT_DIR = "plot"
MAX_LOOKUP_RESULTS = 20


class CorpusPolicyError(ValueError):
    """Raised when a corpus helper request is outside the safe policy."""


@dataclass(frozen=True)
class CharacterMatch:
    id: int
    score: int
    chinese_name: str
    english_name: str
    japanese_name: str
    birthday: str
    title_zh: str
    title_ja: str
    plot_files: list[str]
    file_globs: list[str]
    suggested_search_terms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CorpusInspector:
    """Inspects the local knowledge-base layout and character index."""

    def __init__(self, root: str | Path | None = None):
        self.root = self._resolve_root(root or config.RAG_DIRECTORY)
        self.character_index_path = self.root / CHARACTER_INDEX_FILE
        self.plot_dir = self.root / PLOT_DIR

    def overview(self, *, sample_limit: int = 20) -> dict[str, Any]:
        sample_limit = self._clamp_int(sample_limit, minimum=0, maximum=100)
        markdown_files = sorted(self.root.rglob("*.md"))
        csv_files = sorted(self.root.rglob("*.csv"))
        txt_files = sorted(self.root.rglob("*.txt"))
        pdf_files = sorted(self.root.rglob("*.pdf"))
        plot_files = sorted(self.plot_dir.glob("*.md")) if self.plot_dir.exists() else []

        character_rows = self._load_character_rows()
        top_level_files = [
            path.relative_to(self.root).as_posix()
            for path in sorted(self.root.iterdir())
            if path.is_file()
        ]
        return {
            "status": "success",
            "root": str(self.root),
            "layout": {
                "character_index": CHARACTER_INDEX_FILE
                if self.character_index_path.exists()
                else None,
                "plot_markdown_glob": "plot/*.md" if self.plot_dir.exists() else None,
                "top_level_files": top_level_files,
            },
            "counts": {
                "character_rows": len(character_rows),
                "plot_markdown_files": len(plot_files),
                "markdown_files": len(markdown_files),
                "csv_files": len(csv_files),
                "txt_files": len(txt_files),
                "pdf_files": len(pdf_files),
            },
            "csv_files": [path.relative_to(self.root).as_posix() for path in csv_files],
            "sample_plot_files": [
                path.relative_to(self.root).as_posix() for path in plot_files[:sample_limit]
            ],
            "agent_workflow": [
                "Call grep_lookup_character when the user names a character in Chinese, English, or Japanese.",
                "Use the returned file_globs to constrain grep_search/grep_search_many to the character's own plot file.",
                "Search terms are literal and should match the text as it appears in the corpus.",
            ],
        }

    def lookup_character(self, query: str, *, max_results: int = 5) -> dict[str, Any]:
        query = self._validate_query(query)
        max_results = self._clamp_int(max_results, minimum=1, maximum=MAX_LOOKUP_RESULTS)
        query_norm = self._normalize(query)

        matches: list[tuple[int, dict[str, str]]] = []
        for row in self._load_character_rows():
            score = self._score_character_row(row, query=query, query_norm=query_norm)
            if score > 0:
                matches.append((score, row))

        matches.sort(
            key=lambda item: (
                item[0],
                self._get_field(item[1], "赛马娘中文名"),
                self._get_field(item[1], "赛马娘日语名"),
            ),
            reverse=True,
        )
        character_matches = [
            self._build_character_match(idx, score, row)
            for idx, (score, row) in enumerate(matches[:max_results], start=1)
        ]
        return {
            "status": "success",
            "query": query,
            "character_index": self._relative_or_none(self.character_index_path),
            "matched_count": len(matches),
            "returned_count": len(character_matches),
            "matches": [match.to_dict() for match in character_matches],
        }

    def best_character_scope(self, query: str) -> dict[str, Any]:
        lookup = self.lookup_character(query, max_results=1)
        matches = lookup.get("matches", [])
        if not matches:
            return {
                "status": "error",
                "message": f"no character matched: {query}",
                "lookup": lookup,
            }
        match = matches[0]
        file_globs = match.get("file_globs", [])
        if not file_globs:
            return {
                "status": "error",
                "message": f"character matched but no plot file was found: {query}",
                "character": match,
            }
        return {
            "status": "success",
            "character": match,
            "file_globs": ",".join(file_globs),
        }

    def _load_character_rows(self) -> list[dict[str, str]]:
        if not self.character_index_path.exists():
            return []
        with self.character_index_path.open("r", encoding="utf-8-sig", newline="") as fp:
            return list(csv.DictReader(fp))

    def _build_character_match(
        self,
        idx: int,
        score: int,
        row: dict[str, str],
    ) -> CharacterMatch:
        chinese_name = self._get_field(row, "赛马娘中文名")
        english_name = self._get_field(row, "赛马娘英语名")
        japanese_name = self._get_field(row, "赛马娘日语名")
        plot_files = self._find_plot_files(japanese_name)
        file_globs = plot_files or ([f"plot/*{japanese_name}*.md"] if japanese_name else [])
        suggested_search_terms = [
            item
            for item in [japanese_name, chinese_name, english_name]
            if item
        ]
        return CharacterMatch(
            id=idx,
            score=score,
            chinese_name=chinese_name,
            english_name=english_name,
            japanese_name=japanese_name,
            birthday=self._get_field(row, "赛马娘生日"),
            title_zh=self._get_field(row, "赛马娘特殊称号(二つ名)(中文名)"),
            title_ja=self._get_field(row, "赛马娘特殊称号(二つ名)(日语名)"),
            plot_files=plot_files,
            file_globs=file_globs,
            suggested_search_terms=suggested_search_terms,
        )

    def _find_plot_files(self, japanese_name: str) -> list[str]:
        if not japanese_name or not self.plot_dir.exists():
            return []
        files = sorted(self.plot_dir.glob(f"*-{japanese_name}.md"))
        if not files:
            files = sorted(self.plot_dir.glob(f"*{japanese_name}*.md"))
        return [path.relative_to(self.root).as_posix() for path in files]

    def _score_character_row(
        self,
        row: dict[str, str],
        *,
        query: str,
        query_norm: str,
    ) -> int:
        fields = [
            self._get_field(row, "赛马娘中文名"),
            self._get_field(row, "赛马娘英语名"),
            self._get_field(row, "赛马娘日语名"),
        ]
        best = 0
        query_lower = query.lower()
        for field in fields:
            if not field:
                continue
            field_norm = self._normalize(field)
            field_lower = field.lower()
            if field_norm == query_norm:
                best = max(best, 100)
            elif query_norm and (query_norm in field_norm or field_norm in query_norm):
                best = max(best, 80)
            elif query_lower in field_lower or field_lower in query_lower:
                best = max(best, 70)
        return best

    def _normalize(self, value: str) -> str:
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def _validate_query(self, query: str) -> str:
        if not isinstance(query, str):
            raise CorpusPolicyError("query must be a string")
        value = query.strip()
        if not value:
            raise CorpusPolicyError("query must not be empty")
        if len(value) > 120:
            raise CorpusPolicyError("query is too long")
        if re.search(r"[\x00\r\n]", value):
            raise CorpusPolicyError("query must be a single-line string")
        return value

    def _get_field(self, row: dict[str, str], name: str) -> str:
        return (row.get(name) or "").strip()

    def _relative_or_none(self, path: Path) -> str | None:
        if not path.exists():
            return None
        return path.relative_to(self.root).as_posix()

    def _resolve_root(self, root: str | Path) -> Path:
        resolved = Path(root).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"corpus root does not exist: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"corpus root is not a directory: {resolved}")
        return resolved

    def _clamp_int(self, value: int, *, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise CorpusPolicyError("numeric option must be an integer")
        return max(minimum, min(number, maximum))
