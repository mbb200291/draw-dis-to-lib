import pytest

from lib.colors import BINS_MINUTES, COLORS_HEX, minutes_to_color, minutes_to_bin_label


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
