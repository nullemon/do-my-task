from newsalert.config import Watchlist, WatchlistEntry
from newsalert.dedupe import StoryFeatures, event_hint, item_features, match_story, title_tokens, token_similarity
from newsalert.watchlist import WatchlistIndex, subject_key

INDEX = WatchlistIndex(Watchlist(entries=[
    WatchlistEntry(name="Attack on Titan", kind="series", category="anime", aliases=["Shingeki no Kyojin", "進撃の巨人"]),
    WatchlistEntry(name="Spy × Family", kind="series", category="anime", aliases=["Spy x Family"]),
    WatchlistEntry(name="Friends", kind="series", category="tv", match_risk=True),
]))


def test_watchlist_matches_english_japanese_and_aliases():
    assert [m.entry.name for m in INDEX.find("「進撃の巨人」新作アニメ制作決定")] == ["Attack on Titan"]
    assert [m.entry.name for m in INDEX.find("Shingeki no Kyojin final film dated")] == ["Attack on Titan"]
    assert [m.entry.name for m in INDEX.find("SPY x FAMILY season 3 announced")] == ["Spy × Family"]
    assert INDEX.find("Titanic actor news") == []           # word boundaries
    assert INDEX.canonical("Shingeki no Kyojin") == subject_key("Attack on Titan")


def test_event_hints():
    assert event_hint("Legendary voice actor dies at 80") == "death"
    assert event_hint("「鬼滅の刃」最終章の公開が延期") == "delay"
    assert event_hint("Show X cancelled at Netflix") == "cancellation"
    assert event_hint("Some general update") is None


def test_token_similarity_handles_japanese():
    a = title_tokens("「呪術廻戦」第3期の放送決定")
    b = title_tokens("呪術廻戦 第3期 放送決定！")
    assert token_similarity(a, b) > 0.6


def _story(sid, subject, event, entities=(), titles=()):
    return StoryFeatures(sid, subject_key(subject), event, set(entities),
                         [item_features(t, "", INDEX).tokens for t in titles])


def test_match_same_entity_same_event_joins():
    f = item_features("Attack on Titan film delayed to 2027", "", INDEX)
    d = match_story(f, [_story(1, "Attack on Titan", "delay", ["Attack on Titan"], ["New AoT film pushed"])],
                    title_similarity=0.5)
    assert d.story_id == 1


def test_match_same_entity_different_event_does_not_join():
    f = item_features("Attack on Titan wins award", "", INDEX)
    d = match_story(f, [_story(1, "Attack on Titan", "delay", ["Attack on Titan"], ["AoT film delayed"])],
                    title_similarity=0.5)
    assert d.story_id is None and d.ambiguous == []


def test_match_unclear_event_is_ambiguous():
    f = item_features("Attack on Titan staff share message", "", INDEX)
    d = match_story(f, [_story(1, "Attack on Titan", "announcement", ["Attack on Titan"], ["AoT new project revealed"])],
                    title_similarity=0.5)
    assert d.story_id is None and d.ambiguous == [1]


def test_match_risk_entity_alone_does_not_join():
    f = item_features("Friends of the victim gather", "", INDEX)
    d = match_story(f, [_story(1, "Friends", "other", ["Friends"], ["Friends reunion special"])], title_similarity=0.5)
    assert d.story_id is None and d.ambiguous == []


def test_near_identical_headlines_join_without_entities():
    f = item_features("Pop star Jane Roe announces world tour dates", "", INDEX)
    d = match_story(f, [_story(1, "Jane Roe", "announcement", [], ["Pop star Jane Roe announces world tour"])],
                    title_similarity=0.5)
    assert d.story_id == 1


def test_shared_name_alone_is_not_headline_overlap():
    f = item_features("Statement from Attack on Titan staff", "", INDEX)
    d = match_story(f, [_story(1, "Attack on Titan", "other", ["Attack on Titan"], ["Attack on Titan posts message"])],
                    title_similarity=0.5)
    assert d.story_id is None and d.ambiguous == [1]   # goes to the AI tie-break instead
