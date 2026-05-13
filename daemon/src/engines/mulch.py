import os
import yaml
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

MULCH_ROOT = "/Users/albin/Documents/cliently/.mulch"

class MulchManager:
    def __init__(self, root: str = MULCH_ROOT):
        self.root = root
        self.config = {}
        self._load_config()

    def _load_config(self):
        config_path = os.path.join(self.root, "mulch.config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)

    def get_domain_info(self) -> str:
        """Get summary of mulch domains for LLM context."""
        domains = self.config.get("domains", {})
        if not domains:
            return "No mulch domains configured."
            
        lines = ["--- MULCH DOMAIN CONVENTIONS ---"]
        for domain, cfg in domains.items():
            types = ", ".join(cfg.get("allowed_types", []))
            lines.append(f"- {domain.upper()}: Supports {types}")
        return "\n".join(lines)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Expose mulch tools to Gemini."""
        return [
            {
                "name": "query_mulch_conventions",
                "description": "Query domain-specific conventions, patterns, and past failures from the Mulch system. Use this to ensure parallel agents adhere to project-wide standards.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "enum": list(self.config.get("domains", {}).keys()),
                            "description": "The technical domain (auth, api, mobile, payments, core)."
                        },
                        "query_type": {
                            "type": "string",
                            "description": "Type of information needed (convention, pattern, failure, decision)."
                        }
                    },
                    "required": ["domain", "query_type"]
                }
            }
        ]

    def execute_query(self, domain: str, query_type: str) -> Dict[str, Any]:
        """Execute a mulch query (mocked for now, looking at filesystem)."""
        domain_path = os.path.join(self.root, domain)
        if not os.path.exists(domain_path):
            return {"error": f"Domain {domain} not found in Mulch."}
            
        # In a real implementation, we'd search for files or DB entries here.
        return {
            "status": "success",
            "domain": domain,
            "type": query_type,
            "findings": [f"Standard {domain} {query_type} applied."]
        }

# Global singleton
mulch_manager = MulchManager()
