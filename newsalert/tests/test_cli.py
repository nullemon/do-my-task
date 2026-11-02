import argparse
import time

import pytest

from newsalert.cli import parse_duration, stats_report


def test_parse_duration():
    assert parse_duration("30m") == 1800
    assert parse_duration("2h") == 7200
    assert parse_duration("1d") == 86400
    assert parse_duration("45") == 2700  # bare number = minutes
    with pytest.raises(argparse.ArgumentTypeError):
        parse_duration("soon")


def test_stats_report_latency_alerts_and_cost(db):
    now = time.time()
    for i, (src, pub_ago, alert_after_fetch) in enumerate([("TMZ", 70, 2.0), ("TMZ", 130, 4.0), ("ANN", 50, 1.0)]):
        cur = db.conn.execute(
            "INSERT INTO items (source, source_type, trust, category, source_group, title, text, text_hash, published_at, fetched_at, status) "
            "VALUES (?, 'rss', 'major', 'celebrity', ?, 't', 't', '', ?, ?, 'new')",
            (src, src, now - pub_ago, now - 10),
        )
        sid = db.create_story(first_item_id=cur.lastrowid, published_at=now - pub_ago, fetched_at=now - 10,
                              alerted_at=now - 10 + alert_after_fetch, status="alerted", confidence="SINGLE OUTLET")
        db.record_alert(story_id=sid, kind="ring", urgency="normal", title="t", message="m", channel="ntfy", ok=True)
    db.record_alert(story_id=None, kind="health", urgency="normal", title="t", message="m", channel="ntfy", ok=False, error="x")
    db.record_usage(purpose="triage", model="claude-haiku-5-5", input_tokens=200, output_tokens=50,
                    cost_usd=0.000045, latency_ms=600, ok=True)
    db.update_source_state("Variety", failing_since=now - 700, last_error="HTTP 403")
    report = stats_report(db, 24, now=now)
    assert "TMZ" in report and "ANN" in report
    tmz = next(line for line in report.splitlines() if line.strip().startswith("TMZ"))
    assert " 2 " in tmz and "1m" in tmz             # 2 alerts, median ~1m4s
    assert "ring/normal=3" in report and "failed deliveries: 1" in report
    assert "1 calls (1 ok" in report and "$0.0000" in report
    assert "Variety" in report and "HTTP 403" in report
