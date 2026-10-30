"""Gate de mix de tipos — funções puras (T2).

Unit, sem DB. Valida group_by_type_band e filter_valid_groups.
"""

from app.tenis_degradation.mix_gate import filter_valid_groups, group_by_type_band


def _run(tipo, pace_s, distance_m=5000):
    return {
        "inferred_type": tipo,
        "pace_s": pace_s,
        "distance_m": distance_m,
    }


def test_group_by_type_band() -> None:
    """Done-when T2: agrupa por tipo × banda de pace."""
    runs = [
        _run("facil", 360),
        _run("facil", 370),
        _run("tempo", 300),
    ]
    groups = group_by_type_band(runs)
    assert ("facil", "facil") in groups
    assert len(groups[("facil", "facil")]) == 2
    assert ("tempo", "tempo") in groups  # pace 300 -> banda "tempo"
    assert len(groups[("tempo", "tempo")]) == 1


def test_filter_valid_groups() -> None:
    """Done-when T2: remove grupos com poucas corridas."""
    groups = {
        ("facil", "facil"): [_run("facil", 360), _run("facil", 370)],
        ("tempo", "tempo"): [_run("tempo", 300)],
    }
    filtered = filter_valid_groups(groups, min_pairs=2)
    assert ("facil", "facil") in filtered
    assert ("tempo", "tempo") not in filtered
