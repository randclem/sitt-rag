import pytest

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
