from agent.agent import InvoiceAgent


class FakeLLM:
    def ask(self, prompt: str) -> str:
        return '["Find invoice INV-001", "Read invoice amount", "Report invoice amount"]'


agent = InvoiceAgent(FakeLLM())

state = agent.run(
    "Find invoice INV-001 and report its amount"
)

print("\n--- MOCK AGENT RESULT ---")
print("Plan:", state.plan)
print("Actions:", state.actions_taken)
print("Observations:", state.observations)
print("Success:", state.success)
print("Finished:", state.finished)
