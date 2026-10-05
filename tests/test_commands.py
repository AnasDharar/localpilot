from assistant.commands import normalize_timer_duration
from assistant.actions import TOOLS, close_application, open_website


def test_spoken_timer_durations_are_normalized_before_needle():
    assert normalize_timer_duration("Set a timer for one minute") == "Set a timer for 60 seconds"
    assert normalize_timer_duration("Set a timer for five minutes") == "Set a timer for 300 seconds"
    assert normalize_timer_duration("Set a timer for 30 seconds") == "Set a timer for 30 seconds"


def test_close_application_is_in_the_fixed_needle_toolset():
    assert close_application in TOOLS


def test_open_website_is_in_the_fixed_needle_toolset():
    assert open_website in TOOLS
