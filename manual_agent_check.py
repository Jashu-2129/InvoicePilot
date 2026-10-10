from agent.agent import InvoiceAgent


class FakeLLM:
    """Simulates an LLM without using API credits."""

    def ask(self, prompt: str) -> str:
        return '["Find invoice INV-999"]'


agent = InvoiceAgent(FakeLLM())

state = agent.run(
    "Find invoice INV-999"
)

print("Goal:", state.user_goal)
print("Plan:", state.plan)
print("Actions:", state.actions_taken)
print("Observations:", state.observations)
print("Success:", state.success)
print("Finished:", state.finished)
