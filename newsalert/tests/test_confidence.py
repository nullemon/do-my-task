import itertools

import pytest

from newsalert.confidence import (
    CONFIRMED, DEATH_WARNING, OFFICIAL, SINGLE, UNCONFIRMED, SourceRef, is_upgrade, label_for, needs_death_warning,
)


def refs(*specs):
    return [SourceRef(name=f"{t}-{g}", trust=t, group=g) for t, g in specs]


@pytest.mark.parametrize(
    "sources, expected",
    [
        ([], UNCONFIRMED),
        ([("signal", "wiki")], UNCONFIRMED),
        ([("signal", "wiki"), ("signal", "fan")], UNCONFIRMED),
        ([("major", "ann")], SINGLE),
        ([("major", "ann"), ("signal", "wiki")], SINGLE),
        ([("major", "penske"), ("major", "penske")], SINGLE),          # Variety + Deadline: same owner
        ([("major", "ann"), ("major", "natalie")], CONFIRMED),        # two independent majors
        ([("official", "studio")], OFFICIAL),
        ([("official", "studio"), ("signal", "wiki")], OFFICIAL),
        ([("official", "studio"), ("official", "publisher")], OFFICIAL),
        ([("official", "studio"), ("major", "ann")], CONFIRMED),      # official + major
        ([("official", "studio"), ("major", "ann"), ("signal", "w")], CONFIRMED),
    ],
)
def test_labels_for_each_trust_combination(sources, expected):
    assert label_for(refs(*sources)) == expected


def test_every_combination_of_tiers_is_labelled_sanely():
    tiers = ["official", "major", "signal"]
    for n in range(1, 4):
        for combo in itertools.product(tiers, repeat=n):
            label = label_for(refs(*[(t, f"g{i}") for i, t in enumerate(combo)]))
            if set(combo) == {"signal"}:
                assert label == UNCONFIRMED
            if "signal" in combo and label == CONFIRMED:
                # signals never contribute: confirmation must come from the others alone
                assert label_for(refs(*[(t, f"g{i}") for i, t in enumerate(combo) if t != "signal"])) == CONFIRMED


def test_death_warning_only_for_unconfirmed_deaths():
    assert needs_death_warning("death", UNCONFIRMED)
    assert not needs_death_warning("death", SINGLE)
    assert not needs_death_warning("announcement", UNCONFIRMED)
    assert DEATH_WARNING == "Not confirmed — check before acting."


def test_upgrade_ordering():
    assert is_upgrade(UNCONFIRMED, SINGLE)
    assert is_upgrade(SINGLE, OFFICIAL)
    assert is_upgrade(OFFICIAL, CONFIRMED)
    assert not is_upgrade(CONFIRMED, CONFIRMED)
    assert not is_upgrade(CONFIRMED, SINGLE)
