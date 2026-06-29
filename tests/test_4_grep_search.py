import shutil
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from umamusume_rag.grep import (
    CorpusInspector,
    GrepPolicyError,
    RipgrepSearcher,
)


pytestmark = pytest.mark.skipif(
    shutil.which("rg") is None,
    reason="ripgrep is not installed",
)


def test_grep_search_returns_literal_matches(tmp_path):
    (tmp_path / "story.md").write_text(
        "スペシャルウィーク は元気です。\n"
        "トレーナーと話しました。\n"
        "もう一度 スペシャルウィーク が走ります。\n",
        encoding="utf-8",
    )

    searcher = RipgrepSearcher(root=tmp_path)
    result = searcher.search("スペシャルウィーク", max_results=5, context_lines=1)

    assert result["status"] == "success"
    assert result["match_count"] == 2
    assert result["returned_count"] == 2
    assert result["files_with_matches"] == 1
    assert result["results"][0]["file"] == "story.md"
    assert "トレーナー" in result["results"][0]["context"]


def test_grep_search_uses_fixed_strings_not_regex(tmp_path):
    (tmp_path / "regex.md").write_text(
        "abc.* should match literally\n"
        "abc123 should not match the literal pattern\n",
        encoding="utf-8",
    )

    searcher = RipgrepSearcher(root=tmp_path)
    result = searcher.search("abc.*", max_results=5, context_lines=0)

    assert result["status"] == "success"
    assert result["match_count"] == 1
    assert result["results"][0]["line"] == "abc.* should match literally"


def test_grep_search_rejects_path_escape_glob(tmp_path):
    (tmp_path / "story.md").write_text("メジロマックイーン\n", encoding="utf-8")

    searcher = RipgrepSearcher(root=tmp_path)
    with pytest.raises(GrepPolicyError):
        searcher.search("メジロ", file_globs="../*.md")


def test_corpus_lookup_character_returns_plot_scope(tmp_path):
    (tmp_path / "plot").mkdir()
    (tmp_path / "plot" / "1003-トウカイテイオー.md").write_text(
        "# トウカイテイオー (`1003`)\n### 菊花賞に出るんだ！\n",
        encoding="utf-8",
    )
    (tmp_path / "umamusume_character_baseinfo.csv").write_text(
        "赛马娘中文名,赛马娘英语名,赛马娘日语名,赛马娘生日,三围,身高(cm),声优(cv),"
        "赛马娘特殊称号(二つ名)(中文名),赛马娘特殊称号(二つ名)(日语名),赛马娘特殊称号获取条件\n"
        "东海帝王,Tokai Teio,トウカイテイオー,4月20日,B77·W54·H76,150,Machico,帝王,帝王,条件\n",
        encoding="utf-8",
    )

    inspector = CorpusInspector(root=tmp_path)
    result = inspector.lookup_character("东海帝王")

    assert result["status"] == "success"
    assert result["matched_count"] == 1
    match = result["matches"][0]
    assert match["japanese_name"] == "トウカイテイオー"
    assert match["plot_files"] == ["plot/1003-トウカイテイオー.md"]
    assert match["file_globs"] == ["plot/1003-トウカイテイオー.md"]


def test_corpus_overview_reports_index_and_plot_files(tmp_path):
    (tmp_path / "plot").mkdir()
    (tmp_path / "plot" / "1003-トウカイテイオー.md").write_text("本文\n", encoding="utf-8")
    (tmp_path / "umamusume_character_baseinfo.csv").write_text(
        "赛马娘中文名,赛马娘英语名,赛马娘日语名\n"
        "东海帝王,Tokai Teio,トウカイテイオー\n",
        encoding="utf-8",
    )

    result = CorpusInspector(root=tmp_path).overview()

    assert result["status"] == "success"
    assert result["layout"]["character_index"] == "umamusume_character_baseinfo.csv"
    assert result["counts"]["character_rows"] == 1
    assert result["counts"]["plot_markdown_files"] == 1
