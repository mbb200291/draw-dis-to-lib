import pytest

from lib.colors import (
    BINS_MINUTES,
    COLORS_HEX,
    DISTANCE,
    DRIVING,
    WALKING,
    minutes_to_color,
    minutes_to_bin_label,
)


def test_bins_and_colors_align():
    # COLORS_HEX 數量比 BINS_MINUTES 多 1（n 個 cut 點分成 n+1 個 bin）
    assert len(COLORS_HEX) == len(BINS_MINUTES) + 1


@pytest.mark.parametrize(
    "minutes,expected_hex",
    [
        (0.0, "#1a9641"),       # 0-5 深綠
        (4.9, "#1a9641"),
        (5.0, "#a6d96a"),       # 5-10 淺綠（左閉右開）
        (12.0, "#ffffbf"),      # 10-15 黃
        (18.0, "#fdae61"),      # 15-20 橙
        (25.0, "#d7191c"),      # 20-30 紅
        (60.0, "#7a0177"),      # 30+ 暗紅
        (999.0, "#7a0177"),
    ],
)
def test_minutes_to_color_table(minutes, expected_hex):
    assert minutes_to_color(minutes) == expected_hex


def test_minutes_to_color_negative_raises():
    with pytest.raises(ValueError):
        minutes_to_color(-1.0)


def test_minutes_to_bin_label():
    assert minutes_to_bin_label(0.0) == "0–5"
    assert minutes_to_bin_label(7.5) == "5–10"
    assert minutes_to_bin_label(60.0) == "30+"


# === New: per-scale tests ===

@pytest.mark.parametrize(
    "scale,n_bins",
    [(DRIVING, 6), (WALKING, 6), (DISTANCE, 6)],
)
def test_scale_has_consistent_bin_count(scale, n_bins):
    assert len(scale.cuts) + 1 == n_bins
    assert len(scale.colors) == n_bins
    assert len(scale.labels) == n_bins


def test_walking_scale_buckets():
    # walking is on a much wider time scale than driving
    assert WALKING.label(10) == "0–15"
    assert WALKING.label(25) == "15–30"
    assert WALKING.label(45) == "30–60"
    assert WALKING.label(75) == "60–90"
    assert WALKING.label(100) == "90–120"
    assert WALKING.label(180) == "120+"


def test_distance_scale_buckets():
    assert DISTANCE.label(0.5) == "0–2"
    assert DISTANCE.label(3) == "2–5"
    assert DISTANCE.label(7) == "5–10"
    assert DISTANCE.label(12) == "10–15"
    assert DISTANCE.label(17) == "15–20"
    assert DISTANCE.label(25) == "20+"


def test_driving_backward_compat_matches_scale():
    """Module-level minutes_to_color must equal DRIVING.color()."""
    for v in (0, 4.9, 5, 12, 25, 60):
        assert minutes_to_color(v) == DRIVING.color(v)
