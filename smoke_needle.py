"""Harmless Needle tool-selection smoke test; defines no system-control tools."""
import needle

@needle.tool
def echo_text(text: str) -> str:
    """Echo supplied text exactly."""
    return text

def run_smoke() -> dict:
    """Run the only tool this smoke test makes available."""
    agent = needle.Needle(tools=[echo_text])
    return agent.run("Please echo the text: LocalPilot smoke test")


if __name__ == "__main__":
    response = run_smoke()
    print("Function calls:", response.get("function_calls", []))
    print("Results:", response.get("results", []))
    print("Confidence:", response.get("confidence"))
