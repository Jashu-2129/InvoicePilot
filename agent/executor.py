

from agent.state import AgentState
from tools.registry import ToolRegistry


class Executor:
    """Executes approved tool calls for the AI agent."""

    def __init__(self, registry=None):
        self.registry = registry or ToolRegistry()

    def execute_tool(
        self,
        state: AgentState,
        tool_name: str,
        **arguments,
    ) -> dict:
        """Execute a registered tool and record its result."""

        result = self.registry.execute(tool_name, **arguments)

        state.current_step += 1
        state.actions_taken.append(
            f"{tool_name} with {arguments}"
        )

        state.data["last_result"] = result

        return result