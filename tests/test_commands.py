from assistant.commands import normalize_timer_duration


def test_spoken_timer_durations_are_normalized_before_needle():
    assert normalize_timer_duration("Set a timer for one minute") == "Set a timer for 60 seconds"
    assert normalize_timer_duration("Set a timer for five minutes") == "Set a timer for 300 seconds"
    assert normalize_timer_duration("Set a timer for 30 seconds") == "Set a timer for 30 seconds"
