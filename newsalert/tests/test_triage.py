import asyncio
import json
from types import SimpleNamespace

from newsalert.config import TriageSettings
from newsalert.triage import HaikuTriager, TriageInput


def response(payload, stop="end_turn", inp=180, out=60):
    return SimpleNamespace(
        stop_reason=stop,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=json.dumps(payload))],
        usage=SimpleNamespace(input_tokens=inp, output_tokens=out),
    )


class Messages:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.kwargs = result, exc, None

    async def create(self, **kw):
        self.kwargs = kw
        if self.exc:
            raise self.exc
        return self.result


ITEM = TriageInput(source="ANN", trust="major", category="anime", title="Studio X announces Season 2 of Y",
                   text="Studio X announced a second season.", watchlist_names=["Y"])


async def test_parses_valid_triage_and_records_cost(db):
    payload = {"relevant": True, "category": "anime", "event_type": "announcement", "subject": "Y",
               "importance": 7, "is_rumor": False,
               "summary": " ".join(["word"] * 40)}
    msgs = Messages(response(payload))
    t = HaikuTriager(TriageSettings(), db=db, client=SimpleNamespace(messages=msgs))
    r = await t.triage(ITEM)
    assert r.ai_ok and r.relevant and r.subject == "Y" and r.event_type == "announcement"
    assert r.importance == 5                       # clamped
    assert len(r.summary.split()) == 25            # max 25 words
    kw = msgs.kwargs
    assert kw["model"] == "claude-haiku-5-5"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["output_config"]["effort"] == "low"
    assert "<item>" in kw["messages"][0]["content"]
    row = db.conn.execute("SELECT * FROM usage").fetchone()
    assert row["ok"] == 1 and row["input_tokens"] == 180
    assert abs(row["cost_usd"] - (180 * 0.10 + 60 * 0.50) / 1e6) < 1e-12


async def test_refusal_falls_back_to_headline(db):
    t = HaikuTriager(TriageSettings(), db=db, client=SimpleNamespace(messages=Messages(response({}, stop="refusal"))))
    r = await t.triage(ITEM)
    assert not r.ai_ok and r.summary is None and r.relevant
    assert "refusal" in r.error


async def test_api_error_falls_back(db):
    t = HaikuTriager(TriageSettings(), db=db, client=SimpleNamespace(messages=Messages(exc=ConnectionError("boom"))))
    r = await t.triage(ITEM)
    assert not r.ai_ok and "boom" in r.error and r.event_type == "announcement"


async def test_timeout_is_enforced(db):
    class Slow:
        async def create(self, **kw):
            await asyncio.sleep(5)

    t = HaikuTriager(TriageSettings(timeout_seconds=0.1), db=db, client=SimpleNamespace(messages=Slow()))
    r = await asyncio.wait_for(t.triage(ITEM), 1)
    assert not r.ai_ok and "timeout" in r.error


async def test_tiebreak(db):
    t = HaikuTriager(TriageSettings(), db=db,
                     client=SimpleNamespace(messages=Messages(response({"same_event": True}))))
    assert await t.same_event("a", "b") is True
