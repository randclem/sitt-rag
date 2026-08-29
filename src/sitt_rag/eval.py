"""Retrieval-quality eval: Recall@5 for `search_cryptid_lore` over a golden query set.

Purely informational — always exits 0, with no pass/fail threshold.

Usage: python -m sitt_rag.eval
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sitt_rag.config import GOLDEN_QUERIES_PATH
from sitt_rag.embeddings import EmbeddingError

MECHANICAL_TEMPLATE = "Tell me about {name}"
RECALL_AT = 5


@dataclass
class GoldenQuery:
    query: str
    expected: list[str]
    kind: str


class EvalError(Exception):
    pass


def _read_golden_file(path: Path) -> dict:
    """Load the golden file as a dict, turning every read/parse failure into an `EvalError`."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvalError(f"golden query file not found at {path}") from exc
    except ValueError as exc:
        raise EvalError(f"golden query file at {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise EvalError(f"golden query file at {path} must be a JSON object, not {type(data).__name__}")
    return data


def load_golden_queries(path: Path = GOLDEN_QUERIES_PATH) -> list[GoldenQuery]:
    """Read the checked-in golden set: mechanical entries first, then thematic."""
    data = _read_golden_file(path)

    queries: list[GoldenQuery] = []
    for kind in ("mechanical", "thematic"):
        for entry in data.get(kind, []):
            query = entry.get("query")
            expected = entry.get("expected")
            if not query or not isinstance(expected, list):
                raise EvalError(f"{kind} entry {entry!r} needs a 'query' and an 'expected' list")
            if not expected:
                # A query with nothing expected can never pass; it would quietly
                # drag the aggregate score down forever.
                raise EvalError(f"{kind} query {query!r} lists no expected cryptids")
            queries.append(GoldenQuery(query=query, expected=list(expected), kind=kind))
    return queries


def mechanical_queries(names: list[str]) -> list[GoldenQuery]:
    """One base query per ingested cryptid: "Tell me about X" should retrieve X."""
    return [
        GoldenQuery(query=MECHANICAL_TEMPLATE.format(name=name), expected=[name], kind="mechanical")
        for name in names
    ]


@dataclass
class Hit:
    cryptid_name: str
    score: float


@dataclass
class QueryOutcome:
    golden: GoldenQuery
    hits: list[Hit]
    passed: bool
    matched: str | None = None
    error: str | None = None

    @property
    def retrieved(self) -> list[str]:
        return [hit.cryptid_name for hit in self.hits]


@dataclass
class EvalReport:
    results: list[QueryOutcome]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def percentage(self) -> float:
        return 100.0 * self.passed / self.total if self.total else 0.0

    @property
    def failures(self) -> list[QueryOutcome]:
        return [result for result in self.results if not result.passed]


def evaluate(golden_queries: list[GoldenQuery], search, top_k: int = RECALL_AT) -> EvalReport:
    """Run every golden query through `search` and score it as Recall@`top_k`.

    A query passes if *any* of its expected cryptids appears in the top `top_k`
    results — thematic queries have several valid answers competing for the
    same handful of slots.
    """
    results: list[QueryOutcome] = []
    for golden in golden_queries:
        hits = search(golden.query, top_k)
        # `search_cryptid_lore` answers failures with an `{error: {code, message}}`
        # envelope rather than raising; a broken query scores as a miss, not a crash.
        if isinstance(hits, dict):
            error = hits.get("error", {})
            results.append(
                QueryOutcome(
                    golden=golden,
                    hits=[],
                    passed=False,
                    error=f"{error.get('code', 'error')}: {error.get('message', '')}",
                )
            )
            continue
        found = [Hit(cryptid_name=hit["cryptid_name"], score=hit["score"]) for hit in hits]
        retrieved = [hit.cryptid_name for hit in found]
        matched = next((name for name in golden.expected if name in retrieved), None)
        results.append(QueryOutcome(golden=golden, hits=found, passed=matched is not None, matched=matched))
    return EvalReport(results=results)


def format_report(report: EvalReport) -> str:
    """Render per-query pass/fail plus the aggregate score.

    Passing queries stay one line; failures show what actually came back so a
    near-miss is distinguishable from a query the corpus can't answer at all.
    """
    lines: list[str] = []
    for result in report.results:
        if result.passed:
            lines.append(f"PASS  [{result.golden.kind}] {result.golden.query}  -> {result.matched}")
            continue
        lines.append(f"FAIL  [{result.golden.kind}] {result.golden.query}")
        lines.append(f"        expected any of: {', '.join(result.golden.expected)}")
        if result.error:
            lines.append(f"        search error: {result.error}")
        elif not result.hits:
            lines.append("        top 5: (no results)")
        else:
            lines.append("        top 5:")
            for rank, hit in enumerate(result.hits, start=1):
                lines.append(f"          {rank}. {hit.cryptid_name} ({hit.score:.2f})")

    lines.append("")
    lines.append(f"Recall@{RECALL_AT}: {report.passed}/{report.total} — {report.percentage:.1f}%")
    return "\n".join(lines)


def _default_search(query: str, top_k: int):
    """Go through the real MCP tool, so the eval measures what callers actually get."""
    from sitt_rag import server

    return server.search_cryptid_lore(query, top_k=top_k)


def _store_cryptid_names() -> list[str]:
    from sitt_rag.store import Store

    return [summary.name for summary in Store().list_cryptids() or []]


def _warn_on_drift(queries: list[GoldenQuery]) -> None:
    """Flag a golden set that no longer matches the corpus.

    A stale mechanical section is the quiet failure here: it keeps scoring
    cryptids that are gone and never scores the ones newly ingested.
    """
    try:
        stored = set(_store_cryptid_names())
    except Exception:  # the store is unreadable; the eval run itself will say so
        return
    covered = {name for query in queries if query.kind == "mechanical" for name in query.expected}
    missing = sorted(stored - covered)
    extra = sorted(covered - stored)
    if not missing and not extra:
        return
    print("warning: the golden set has drifted from the store — rerun with --regenerate")
    if missing:
        print(f"  ingested but not in the golden set ({len(missing)}): {', '.join(missing)}")
    if extra:
        print(f"  in the golden set but not ingested ({len(extra)}): {', '.join(extra)}")
    print()


def run(golden_path: Path = GOLDEN_QUERIES_PATH, search=None) -> EvalReport:
    """Score the golden set and print the report. Returns it for programmatic callers."""
    queries = load_golden_queries(golden_path)
    _warn_on_drift(queries)
    print(f"Evaluating {len(queries)} golden queries at Recall@{RECALL_AT}...\n")
    report = evaluate(queries, search=search or _default_search)
    print(format_report(report))
    return report


def regenerate(golden_path: Path = GOLDEN_QUERIES_PATH) -> int:
    """Rewrite the mechanical section from the ingested corpus, leaving thematic queries alone."""
    data = _read_golden_file(golden_path) if golden_path.exists() else {}
    names = sorted(_store_cryptid_names())
    if not names:
        # Regenerating from an un-ingested (or misconfigured) store would replace the
        # hand-maintained file with an empty mechanical section and no way back.
        raise EvalError(
            "the store holds no cryptids — refusing to regenerate the golden set from an empty corpus; "
            "run `python -m sitt_rag.update` first"
        )
    data["mechanical"] = [
        {"query": MECHANICAL_TEMPLATE.format(name=name), "expected": [name]} for name in names
    ]
    data.setdefault("thematic", [])
    golden_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(names)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m sitt_rag.eval",
        description="Score search_cryptid_lore's Recall@5 against the golden query set.",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rebuild the mechanical golden entries from the ingested corpus and exit",
    )
    args = parser.parse_args(argv)

    try:
        if args.regenerate:
            count = regenerate(GOLDEN_QUERIES_PATH)
            print(f"Regenerated {count} mechanical golden queries in {GOLDEN_QUERIES_PATH}.")
            return
        run(GOLDEN_QUERIES_PATH)
    except (EvalError, EmbeddingError) as exc:
        # The score never gates the exit code; not being able to run at all does.
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
