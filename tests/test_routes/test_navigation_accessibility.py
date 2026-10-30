"""Accessible shared navigation in each supported language."""
from html.parser import HTMLParser

import pytest


class NavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.mark.parametrize("language", ["ru", "en", "zh"])
def test_navigation_has_names_and_focusable_skip_target(client, language):
    client.get("/change_language/" + language)
    with client.session_transaction() as session:
        session["pin_authenticated"] = True
    response = client.get("/locked")
    assert response.status_code == 200
    parser = NavigationParser()
    parser.feed(response.text)
    skip = next(attrs for tag, attrs in parser.elements
                if tag == "a" and attrs.get("class") == "skip-content")
    main = next(attrs for tag, attrs in parser.elements if tag == "main")
    assert skip["href"] == "#" + main["id"]
    assert main["tabindex"] == "-1"
    toggles = [attrs for tag, attrs in parser.elements
               if attrs.get("data-bs-toggle") == "dropdown"]
    assert len(toggles) == 3
    assert all(attrs.get("aria-label") for attrs in toggles)
    assert len({attrs["aria-label"] for attrs in toggles}) == 3
    mobile = next(attrs for tag, attrs in parser.elements
                  if attrs.get("data-bs-target") == "#navbarNav")
    assert mobile["aria-controls"] == "navbarNav"
    assert mobile["aria-expanded"] == "false"
    assert mobile["aria-label"]
