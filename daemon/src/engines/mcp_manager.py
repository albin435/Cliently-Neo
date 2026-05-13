import os
import json
import subprocess
import threading
import queue
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MCPServerProxy:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.command = config.get("command")
        self.args = config.get("args", [])
        self.env = config.get("env", {})
        self.process = None
        self.output_queue = queue.Queue()
        self.msg_id = 1
        self.tools = []
        self._running = False
        self._reader_thread = None

    def start(self):
        if self._running:
            return
        
        full_env = {**os.environ, **self.env}
        try:
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=full_env
            )
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self._reader_thread.start()
            logger.info(f"Started MCP Server: {self.name}")
            
            # Initial fetch of tools
            self._fetch_tools()
        except Exception as e:
            logger.error(f"Failed to start MCP Server {self.name}: {e}")

    def stop(self):
        self._running = False
        if self.process:
            self.process.terminate()
            self.process = None

    def _read_stdout(self):
        for line in self.process.stdout:
            if not self._running:
                break
            try:
                msg = json.loads(line)
                self.output_queue.put(msg)
            except json.JSONDecodeError:
                # Log non-JSON output for debugging (some servers might log to stdout)
                logger.debug(f"[{self.name}] {line.strip()}")

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Optional[Dict[str, Any]]:
        if not self._running:
            return None
        
        req_id = self.msg_id
        self.msg_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method
        }
        if params:
            payload["params"] = params
            
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Error sending request to {self.name}: {e}")
            return None

        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Check all items in queue for our ID
                items = []
                while not self.output_queue.empty():
                    item = self.output_queue.get_nowait()
                    if item.get("id") == req_id:
                        return item
                    items.append(item)
                
                # Put back items that are not ours
                for item in items:
                    self.output_queue.put(item)
                    
            except queue.Empty:
                pass
            time.sleep(0.05)
            
        return {"error": "timeout", "id": req_id}

    def _fetch_tools(self):
        resp = self._send_request("tools/list")
        if resp and "result" in resp:
            self.tools = resp["result"].get("tools", [])
            logger.info(f"Fetched {len(self.tools)} tools from {self.name}")
        else:
            logger.warning(f"Failed to fetch tools from {self.name}: {resp}")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._send_request("tools/call", {"name": tool_name, "arguments": arguments}, timeout=30)
        if resp and "result" in resp:
            return resp["result"]
        return resp or {"error": "unknown error"}

class MCPManager:
    def __init__(self, config_path: str = "/Users/albin/.gemini/antigravity/mcp_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServerProxy] = {}
        self.all_tools = []
        
    def load_and_start(self):
        if not os.path.exists(self.config_path):
            logger.warning(f"MCP config not found at {self.config_path}")
            return

        with open(self.config_path, "r") as f:
            config = json.load(f)
            
        server_configs = config.get("mcpServers", {})
        for name, cfg in server_configs.items():
            proxy = MCPServerProxy(name, cfg)
            proxy.start()
            self.servers[name] = proxy
            
        self._refresh_tool_list()

    def _refresh_tool_list(self):
        self.all_tools = []
        for server_name, proxy in self.servers.items():
            for tool in proxy.tools:
                # Namespace tools to avoid collisions?
                # Actually, standard MCP might not expect namespacing, 
                # but for Gemini tools we should probably keep them unique.
                tool_copy = tool.copy()
                # Store which server owns this tool
                tool_copy["_server"] = server_name
                self.all_tools.append(tool_copy)

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to Gemini function declarations."""
        declarations = []
        for tool in self.all_tools:
            decl = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
            declarations.append(decl)
        return declarations

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Find which server has this tool
        for tool in self.all_tools:
            if tool["name"] == tool_name:
                server_name = tool["_server"]
                return self.servers[server_name].call_tool(tool_name, arguments)
        return {"error": f"Tool {tool_name} not found"}

    def stop_all(self):
        for proxy in self.servers.values():
            proxy.stop()

# Global singleton
mcp_manager = MCPManager()
