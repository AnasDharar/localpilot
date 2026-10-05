import smoke_needle


def test_smoke_registers_and_runs_only_echo(monkeypatch):
    seen = {}

    class FakeAgent:
        def __init__(self, tools):
            seen["tools"] = tools

        def run(self, prompt):
            seen["prompt"] = prompt
            return {"results": [seen["tools"][0]("safe")]}

    monkeypatch.setattr(smoke_needle.needle, "Needle", FakeAgent)
    assert smoke_needle.run_smoke()["results"] == ["safe"]
    assert seen["tools"] == [smoke_needle.echo_text]
