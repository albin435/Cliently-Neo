import os
import logging
from typing import List, Dict, Any, Optional
from .mcp_manager import mcp_manager
from .skill_manager import skill_manager
from .mulch import mulch_manager
from .context import CLIENTLY_ROOT

logger = logging.getLogger(__name__)

class ToolManager:
    def __init__(self):
        self.mcp = mcp_manager
        self.skills = skill_manager
        self.mulch = mulch_manager

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Combine MCP tools, Skill tools, and Mulch tools."""
        tools = []
        tools.extend(self.mcp.get_gemini_tools())
        tools.extend(self.skills.get_skill_tools())
        tools.extend(self.mulch.get_tools())
        return tools

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool execution to the appropriate manager."""
        logger.info(f"Routing tool call: {tool_name}")
        
        # Check if it's a skill tool
        if tool_name == "hire_specialized_agent":
            skill_name = arguments.get("skill_name")
            task = arguments.get("task_description")
            
            # Write to the bridge for external pickup
            bridge_path = os.path.join(CLIENTLY_ROOT, ".antigravity_bridge.md")
            try:
                with open(bridge_path, "w", encoding="utf-8") as f:
                    f.write(f"# NEO SPECIALIZED AGENT DIRECTIVE\n\n")
                    f.write(f"## Skill\n{skill_name}\n\n")
                    f.write(f"## Task\n{task}\n\n")
                    f.write(f"## Timestamp\n{os.popen('date').read().strip()}\n")
                
                logger.info(f"Wrote delegation directive for {skill_name} to bridge.")
                return {
                    "status": "delegated",
                    "message": f"Specialized agent hired for {skill_name}. Directive written to bridge.",
                    "instruction": "The agent will pick up the task shortly. You may continue with other work."
                }
            except Exception as e:
                logger.error(f"Failed to write to bridge: {e}")
                return {"error": f"Internal delegation failure: {e}"}
            
        if tool_name == "query_mulch_conventions":
            return self.mulch.execute_query(arguments.get("domain"), arguments.get("query_type"))
            
        # Otherwise, check MCP
        return self.mcp.execute_tool(tool_name, arguments)

# Global singleton
tool_manager = ToolManager()
