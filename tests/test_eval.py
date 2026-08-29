import json
import pytest

from sitt_rag import eval as evaluation
from sitt_rag.config import GOLDEN_QUERIES_PATH


def test_mechanical_queries_expect_their_own_cryptid():
    queries = evaluation.mechanical_queries(["Bunyip", "Mothman"])

    assert [q.query for q in queries] == ["Tell me about Bunyip", "Tell me about Mothman"]
    assert queries[0].expected == ["Bunyip"]
    assert queries[0].kind == "mechanical"


def _result(name: str, score: float = 0.9) -> dict:
    return {
        "text": f"A chunk about the {name}.",
        "cryptid_name": name,
        "score": score,
        "source": {
            "title": name,
            "url": f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
            "license": "CC BY-SA 4.0",
        },
    }


def _search_returning(*names: str):
    """A `search_cryptid_lore` stand-in that always returns `names`, honouring top_k."""

    def search(query: str, top_k: int) -> list[dict]:
        return [_result(name) for name in names][:top_k]

    return search


def test_query_passes_when_any_expected_cryptid_appears_in_top_five():
    golden = [
        evaluation.GoldenQuery(
            query="Scandinavian lake creature folklore",
            expected=["Selma", "Storsjö monster"],
            kind="thematic",
        )
    ]
    search = _search_returning("Ogopogo", "Champ", "Storsjö monster", "Bunyip", "Mothman")

    report = evaluation.evaluate(golden, search=search)

    assert report.results[0].passed is True
    assert report.results[0].matched == "Storsjö monster"


def test_query_fails_when_no_expected_cryptid_is_retrieved():
    golden = [evaluation.GoldenQuery(query="Tell me about Bigfoot", expected=["Bigfoot"], kind="mechanical")]
    search = _search_returning("Ogopogo", "Champ", "Selma", "Bunyip", "Mothman")

    report = evaluation.evaluate(golden, search=search)

    assert report.results[0].passed is False
    assert report.results[0].matched is None
    assert report.results[0].retrieved == ["Ogopogo", "Champ", "Selma", "Bunyip", "Mothman"]


def test_report_aggregates_passes_over_total():
    golden = [
        evaluation.GoldenQuery(query="a", expected=["Bunyip"], kind="mechanical"),
        evaluation.GoldenQuery(query="b", expected=["Mothman"], kind="mechanical"),
        evaluation.GoldenQuery(query="c", expected=["Nowhere"], kind="thematic"),
    ]

    report = evaluation.evaluate(golden, search=_search_returning("Bunyip", "Mothman"))

    assert report.passed == 2
    assert report.total == 3
    assert report.percentage == pytest.approx(66.7, abs=0.05)


def test_search_error_envelope_counts_as_a_failure_without_crashing():
    golden = [evaluation.GoldenQuery(query="Tell me about Bunyip", expected=["Bunyip"], kind="mechanical")]

    def search(query: str, top_k: int) -> dict:
        return {"error": {"code": "embedding_failed", "message": "Voyage timed out"}}

    report = evaluation.evaluate(golden, search=search)

    assert report.results[0].passed is False
    assert report.results[0].retrieved == []
    assert report.results[0].error == "embedding_failed: Voyage timed out"


def test_load_golden_queries_reads_mechanical_and_thematic_sections(tmp_path):
    path = tmp_path / "golden_queries.json"
    path.write_text(
        json.dumps(
            {
                "mechanical": [{"query": "Tell me about Bunyip", "expected": ["Bunyip"]}],
                "thematic": [
                    {"query": "lake monsters of Scotland", "expected": ["Loch Ness Monster"]},
                ],
            }
        ),
        encoding="utf-8",
    )

    queries = evaluation.load_golden_queries(path)

    assert [q.kind for q in queries] == ["mechanical", "thematic"]
    assert queries[0].query == "Tell me about Bunyip"
    assert queries[1].expected == ["Loch Ness Monster"]


def test_load_golden_queries_rejects_an_entry_with_no_expected_cryptids(tmp_path):
    path = tmp_path / "golden_queries.json"
    path.write_text(json.dumps({"thematic": [{"query": "lake monsters", "expected": []}]}), encoding="utf-8")

    with pytest.raises(evaluation.EvalError, match="lake monsters"):
        evaluation.load_golden_queries(path)


def test_load_golden_queries_rejects_a_malformed_entry(tmp_path):
    path = tmp_path / "golden_queries.json"
    path.write_text(json.dumps({"thematic": [{"query": "lake monsters"}]}), encoding="utf-8")

    with pytest.raises(evaluation.EvalError, match="expected"):
        evaluation.load_golden_queries(path)


def test_format_report_details_failures_and_totals():
    golden = [
        evaluation.GoldenQuery(query="Tell me about Bunyip", expected=["Bunyip"], kind="mechanical"),
        evaluation.GoldenQuery(query="Tell me about Bigfoot", expected=["Bigfoot"], kind="mechanical"),
    ]

    def search(query: str, top_k: int) -> list[dict]:
        if "Bunyip" in query:
            return [_result("Bunyip", score=0.88)]
        return [_result("Ogopogo", score=0.42), _result("Champ", score=0.41)]

    text = evaluation.format_report(evaluation.evaluate(golden, search=search))

    assert "PASS" in text and "FAIL" in text
    # A failure shows what actually came back, with scores, so a near-miss is visible.
    assert "Ogopogo" in text
    assert "0.42" in text
    # A pass stays a single line — no result dump.
    assert "0.88" not in text
    assert "1/2" in text
    assert "50.0%" in text


def _write_golden(path, mechanical=(), thematic=()):
    path.write_text(json.dumps({"mechanical": list(mechanical), "thematic": list(thematic)}), encoding="utf-8")
    return path


def test_main_exits_zero_even_when_every_query_fails(tmp_path, monkeypatch, capsys):
    path = _write_golden(tmp_path / "golden_queries.json", mechanical=[{"query": "Tell me about Bigfoot", "expected": ["Bigfoot"]}])
    monkeypatch.setattr(evaluation, "GOLDEN_QUERIES_PATH", path)
    monkeypatch.setattr(evaluation, "_default_search", _search_returning("Ogopogo"))
    monkeypatch.setattr(evaluation, "_store_cryptid_names", lambda: ["Bigfoot"])

    assert evaluation.main([]) is None

    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "0/1" in out
    assert "0.0%" in out


def test_run_warns_when_the_golden_set_has_drifted_from_the_store(tmp_path, monkeypatch, capsys):
    path = _write_golden(tmp_path / "golden_queries.json", mechanical=[{"query": "Tell me about Bunyip", "expected": ["Bunyip"]}])
    monkeypatch.setattr(evaluation, "_store_cryptid_names", lambda: ["Bunyip", "Bigfoot"])

    evaluation.run(path, search=_search_returning("Bunyip"))

    out = capsys.readouterr().out
    assert "Bigfoot" in out
    assert "--regenerate" in out


def test_checked_in_golden_set_is_loadable_and_has_thematic_queries():
    queries = evaluation.load_golden_queries(GOLDEN_QUERIES_PATH)

    thematic = [q for q in queries if q.kind == "thematic"]
    mechanical = [q for q in queries if q.kind == "mechanical"]
    assert len(thematic) == 10
    assert mechanical, "the checked-in golden set should carry a mechanical entry per ingested cryptid"
    assert all(q.query == evaluation.MECHANICAL_TEMPLATE.format(name=q.expected[0]) for q in mechanical)


def test_regenerate_refuses_to_wipe_the_golden_set_from_an_empty_store(tmp_path, monkeypatch):
    path = _write_golden(
        tmp_path / "golden_queries.json",
        mechanical=[{"query": "Tell me about Bunyip", "expected": ["Bunyip"]}],
        thematic=[{"query": "lake monsters", "expected": ["Bunyip"]}],
    )
    monkeypatch.setattr(evaluation, "_store_cryptid_names", lambda: [])

    with pytest.raises(evaluation.EvalError, match="empty"):
        evaluation.regenerate(path)

    # The checked-in set survives intact — an un-ingested store must not destroy it.
    assert json.loads(path.read_text(encoding="utf-8"))["mechanical"]


def test_regenerate_reports_a_corrupt_golden_file_as_an_eval_error(tmp_path, monkeypatch):
    path = tmp_path / "golden_queries.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(evaluation, "_store_cryptid_names", lambda: ["Bunyip"])

    with pytest.raises(evaluation.EvalError, match="not valid JSON"):
        evaluation.regenerate(path)


def test_load_golden_queries_rejects_a_file_that_is_not_an_object(tmp_path):
    path = tmp_path / "golden_queries.json"
    path.write_text(json.dumps(["Tell me about Bunyip"]), encoding="utf-8")

    with pytest.raises(evaluation.EvalError, match="object"):
        evaluation.load_golden_queries(path)
