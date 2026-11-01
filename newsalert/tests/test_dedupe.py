from newsalert.dedupe import is_stale, normalize_url, text_hash


def test_normalize_url_strips_tracking_and_noise():
    a = normalize_url("http://www.Example.com/news/123/?utm_source=rss&b=2&a=1&fbclid=xyz#comments")
    b = normalize_url("https://example.com/news/123?a=1&b=2")
    assert a == b == "https://example.com/news/123?a=1&b=2"


def test_normalize_url_twitter_alias_and_mobile():
    assert normalize_url("https://mobile.twitter.com/Studio/status/1") == normalize_url("https://x.com/Studio/status/1")


def test_normalize_url_keeps_meaningful_params():
    assert normalize_url("https://youtube.com/watch?v=abc") != normalize_url("https://youtube.com/watch?v=def")


def test_normalize_url_none():
    assert normalize_url(None) is None
    assert normalize_url("") is None


def test_text_hash_ignores_case_punctuation_and_urls():
    a = text_hash("BREAKING: Studio X announces Season 2 of Y! https://t.co/abc")
    b = text_hash("breaking studio x announces season 2 of y")
    assert a and a == b


def test_text_hash_keeps_japanese():
    a = text_hash("「呪術廻戦」第3期の放送決定、2026年1月より")
    b = text_hash("「呪術廻戦」第3期の放送決定、2026年2月より")
    assert a and b and a != b


def test_text_hash_skips_very_short_text():
    assert text_hash("New trailer!") == ""


def test_is_stale():
    now = 1_000_000.0
    assert not is_stale(None, now, 30)
    assert not is_stale(now - 29 * 60, now, 30)
    assert is_stale(now - 31 * 60, now, 30)
    assert not is_stale(now + 9 * 3600, now, 30)  # future-dated (bad feed clock) counts as fresh
