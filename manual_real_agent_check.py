from llm.client import LLMClient
from agent.agent import InvoiceAgent


agent = InvoiceAgent(LLMClient())

state = agent.run(
    "Find invoice INV-001 and report its amount. "
    "Do not approve or modify the invoice."
)

print("\n--- REAL LLM AGENT RESULT ---")
print("Goal:", state.user_goal)
print("Plan:", state.plan)
print("Actions:", state.actions_taken)
print("Observations:", state.observations)
print("Success:", state.success)
print("Finished:", state.finished)