import pytest
import requests

from sitt_rag import wikipedia
from sitt_rag.wikipedia import WikipediaError, fetch_article, fetch_redirects, fetch_taxonomy

LIST_HTML = """
<html><body>
<h2>List</h2>
<h3 id="Aquatic">Aquatic or semi-aquatic</h3>
<table>
<tr><th>Name</th><th>Other names</th></tr>
<tr><td><a href="./Bunyip" title="Bunyip">Bunyip</a></td><td>Bahnyip</td></tr>
<tr><td><a href="./Champ_(folklore)" title="Champ (folklore)">Champ</a></td><td></td></tr>
<tr><td><a href="./Nonexistent" title="Nonexistent" class="new">Nonexistent</a></td><td></td></tr>
<tr><td><a href="./Remy_Van_Lierde#Alleged_encounter" title="Remy Van Lierde">Katanga Snake</a></td><td></td></tr>
</table>
<h3 id="Terrestrial">Terrestrial</h3>
<table>
<tr><th>Name</th></tr>
<tr><td><a href="./Yeti" title="Yeti">Yeti</a></td></tr>
</table>
<h2>See also</h2>
</body></html>
"""

ARTICLE_HTML = """
<html><body>
<section data-mw-section-id="0">
<div class="shortdescription" style="display:none">Mythical creature</div>
<p>The bunyip is a creature from Aboriginal mythology<sup class="reference">[1]</sup>, said to lurk in swamps.</p>
</section>
<section data-mw-section-id="1">
<h2>Distribution</h2>
<p>The bunyip is part of traditional beliefs across Australia.</p>
<p>It varies by region.</p>
</section>
<section data-mw-section-id="2">
<h2>See also</h2>
<p>List of lake monsters</p>
</section>
<section data-mw-section-id="3">
<h2>References</h2>
<p>Some citation text.</p>
</section>
</body></html>
"""

NO_PROSE_ARTICLE_HTML = """
<html><body>
<section data-mw-section-id="0">
<h2>See also</h2>
<p>Nothing but a see-also link here.</p>
</section>
</body></html>
"""

REDIRECTS_JSON = {
    "query": {
        "pages": {
            "123": {
                "title": "Bunyip",
                "redirects": [{"title": "Bunyips"}, {"title": "Bunjip"}],
            }
        }
    }
}


class FakeResponse:
    def __init__(self, text: str = "", json_data: dict | None = None, status: int = 200):
        self.text = text
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


class ScriptedGet:
    """Stands in for `requests.get`, replaying scripted outcomes (responses to
    return, exceptions to raise) and counting calls. The last outcome repeats,
    so a single failing outcome means "fails every time"."""

    def __init__(self, *outcomes):
        self._outcomes = outcomes
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        outcome = self._outcomes[min(self.calls - 1, len(self._outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def sleeps(monkeypatch):
    """Record backoff sleeps instead of actually sleeping."""
    recorded: list[float] = []
    monkeypatch.setattr(wikipedia.time, "sleep", recorded.append)
    return recorded


def test_fetch_taxonomy_parses_categories_and_skips_redlinks(monkeypatch):
    monkeypatch.setattr(wikipedia.requests, "get", lambda *a, **k: FakeResponse(text=LIST_HTML))

    refs = fetch_taxonomy()

    assert [(r.name, r.category, r.wikipedia_title) for r in refs] == [
        ("Bunyip", "Aquatic or semi-aquatic", "Bunyip"),
        ("Champ", "Aquatic or semi-aquatic", "Champ (folklore)"),
        ("Katanga Snake", "Aquatic or semi-aquatic", "Remy Van Lierde"),
        ("Yeti", "Terrestrial", "Yeti"),
    ]


def test_fetch_article_keeps_prose_drops_boilerplate_and_citations(monkeypatch):
    monkeypatch.setattr(wikipedia.requests, "get", lambda *a, **k: FakeResponse(text=ARTICLE_HTML))

    article = fetch_article("Bunyip")

    titles = [s.title for s in article.sections]
    assert titles == ["Lead", "Distribution"]
    assert "See also" not in titles
    assert "References" not in titles

    lead_text = article.sections[0].paragraphs[0]
    assert "[1]" not in lead_text
    assert "swamps." in lead_text
    assert article.sections[1].paragraphs == [
        "The bunyip is part of traditional beliefs across Australia.",
        "It varies by region.",
    ]


def test_fetch_article_raises_when_no_prose_content(monkeypatch):
    monkeypatch.setattr(
        wikipedia.requests, "get", lambda *a, **k: FakeResponse(text=NO_PROSE_ARTICLE_HTML)
    )

    with pytest.raises(WikipediaError):
        fetch_article("Nothing")


def test_fetch_article_raises_wikipedia_error_on_http_failure(monkeypatch):
    monkeypatch.setattr(wikipedia.requests, "get", lambda *a, **k: FakeResponse(status=404))

    with pytest.raises(WikipediaError):
        fetch_article("Does Not Exist")


def test_fetch_redirects_returns_alias_titles(monkeypatch):
    monkeypatch.setattr(
        wikipedia.requests, "get", lambda *a, **k: FakeResponse(json_data=REDIRECTS_JSON)
    )

    aliases = fetch_redirects("Bunyip")

    assert aliases == ["Bunyips", "Bunjip"]


def test_fetch_redirects_raises_wikipedia_error_on_http_failure(monkeypatch, sleeps):
    monkeypatch.setattr(wikipedia.requests, "get", lambda *a, **k: FakeResponse(status=404))

    with pytest.raises(WikipediaError):
        fetch_redirects("Does Not Exist")


def test_fetch_redirects_raises_wikipedia_error_on_unparseable_body(monkeypatch, sleeps):
    """The action API can answer 200 with an HTML error page — that must land in the
    failed bucket like any other fetch failure, not escape and abort the run."""

    class NotJsonResponse(FakeResponse):
        def json(self):
            raise requests.exceptions.JSONDecodeError("Expecting value", "<html>", 0)

    monkeypatch.setattr(wikipedia.requests, "get", lambda *a, **k: NotJsonResponse(text="<html>"))

    with pytest.raises(WikipediaError):
        fetch_redirects("Bunyip")


def test_fetch_taxonomy_raises_wikipedia_error_on_http_failure(monkeypatch, sleeps):
    monkeypatch.setattr(wikipedia.requests, "get", lambda *a, **k: FakeResponse(status=404))

    with pytest.raises(WikipediaError):
        fetch_taxonomy()


def test_transient_status_is_retried_until_it_succeeds(monkeypatch, sleeps):
    get = ScriptedGet(FakeResponse(status=503), FakeResponse(text=ARTICLE_HTML))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    article = fetch_article("Bunyip")

    assert get.calls == 2
    assert sleeps == [1]
    assert [s.title for s in article.sections] == ["Lead", "Distribution"]


def test_rate_limit_is_treated_as_transient(monkeypatch, sleeps):
    get = ScriptedGet(FakeResponse(status=429), FakeResponse(text=ARTICLE_HTML))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    fetch_article("Bunyip")

    assert get.calls == 2


def test_timeout_is_retried_three_times_with_exponential_backoff(monkeypatch, sleeps):
    get = ScriptedGet(requests.Timeout("timed out"))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    with pytest.raises(WikipediaError):
        fetch_article("Bunyip")

    assert get.calls == 4  # first attempt plus three retries
    assert sleeps == [1, 2, 4]


def test_connection_error_is_retried(monkeypatch, sleeps):
    get = ScriptedGet(requests.ConnectionError("refused"))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    with pytest.raises(WikipediaError):
        fetch_article("Bunyip")

    assert get.calls == 4


def test_permanent_status_is_not_retried(monkeypatch, sleeps):
    get = ScriptedGet(FakeResponse(status=404))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    with pytest.raises(WikipediaError):
        fetch_article("Does Not Exist")

    assert get.calls == 1
    assert sleeps == []


def test_redirect_loop_is_not_retried(monkeypatch, sleeps):
    get = ScriptedGet(requests.TooManyRedirects("exceeded 30 redirects"))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    with pytest.raises(WikipediaError):
        fetch_article("Loops")

    assert get.calls == 1
    assert sleeps == []


def test_unparseable_article_is_not_retried(monkeypatch, sleeps):
    get = ScriptedGet(FakeResponse(text=NO_PROSE_ARTICLE_HTML))
    monkeypatch.setattr(wikipedia.requests, "get", get)

    with pytest.raises(WikipediaError):
        fetch_article("Nothing")

    assert get.calls == 1
    assert sleeps == []
