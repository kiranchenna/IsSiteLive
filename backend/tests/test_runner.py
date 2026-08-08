from app.checker.runner import _matches_any


def test_empty_patterns_watch_nothing():
    """Opt-in, not opt-out: real pages carry third-party noise (analytics, CSP reports)
    that would otherwise fail checks for reasons unrelated to the app actually working."""
    assert _matches_any("https://example.com/api/patients", []) is False
    assert _matches_any("https://forms.gle/_/DurableDeepLinkUi/cspreport", []) is False


def test_matching_pattern_is_watched():
    assert _matches_any("https://example.com/api/patients", ["*/api/*"]) is True


def test_non_matching_pattern_is_not_watched():
    assert _matches_any("https://example.com/static/logo.png", ["*/api/*"]) is False
