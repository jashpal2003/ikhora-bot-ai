"""Frozen tool allow-list registry."""

from relay.tools.spec import ToolSpec


class ToolRegistry:
    """Registry maintaining available tools and compiling frozen run allow-lists."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Register a certified tool specification."""
        self._tools[spec.name] = spec

    def get(self, tool_name: str) -> ToolSpec | None:
        return self._tools.get(tool_name)

    def freeze_allow_list(self, allowed_names: list[str]) -> dict[str, ToolSpec]:
        """Compile and freeze the tool allow-list for an agent run (P1).
        
        Once frozen, no runtime model output or remote MCP server can expand it.
        """
        return {name: self._tools[name] for name in allowed_names if name in self._tools}
