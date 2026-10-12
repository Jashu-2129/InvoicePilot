from llm.client import LLMClient
from agent.agent import InvoiceAgent


agent = InvoiceAgent(LLMClient())

state = agent.run(
    "Check whether invoice INV-004 requires human approval and is eligible for review."
    "Do not approve or modify the invoice"
)

print("\n--- REAL LLM AGENT RESULT ---")
print("Goal:", state.user_goal)
print("Plan:", state.plan)
print("Actions:", state.actions_taken)
print("Observations:", state.observations)
print("Success:", state.success)
print("Finished:", state.finished)