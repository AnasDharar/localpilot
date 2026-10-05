"""Run LocalPilot's fixed Needle toolset away from the Qt GUI thread."""
from __future__ import annotations

import re

import needle
from PySide6.QtCore import QObject, Signal
from assistant.actions import TOOLS

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def normalize_timer_duration(text: str) -> str:
    """Make simple spoken timer durations explicit for Needle's integer schema."""
    match = re.search(r"\b(?P<value>\d+|" + "|".join(_NUMBER_WORDS) + r")\s*(?P<unit>seconds?|minutes?|hours?)\b", text, re.I)
    if not match:
        return text
    raw = match.group("value").lower()
    value = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]
    unit = match.group("unit").lower()
    multiplier = 3600 if unit.startswith("hour") else 60 if unit.startswith("minute") else 1
    return text[:match.start()] + f"{value * multiplier} seconds" + text[match.end():]


class CommandWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def run(self) -> None:
        try:
            self.completed.emit(needle.Needle(tools=TOOLS).run(normalize_timer_duration(self.text)))
        except Exception as exc:
            self.failed.emit(f"Could not process LocalPilot action: {exc}")
        finally:
            self.finished.emit()
