from jnu_auto_elective.web import BEIJING_TZ, _parse_beijing_start_at


def test_parse_beijing_start_at_naive_datetime():
    parsed = _parse_beijing_start_at("2026-06-25T13:00")

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 6
    assert parsed.day == 25
    assert parsed.hour == 13
    assert parsed.tzinfo == BEIJING_TZ


def test_parse_beijing_start_at_empty():
    assert _parse_beijing_start_at("") is None
