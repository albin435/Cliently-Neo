import os
import yaml
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

SKILLS_PATH = "/Users/albin/.gemini/antigravity/skills"

class SkillManager:
    def __init__(self, skills_dir: str = SKILLS_PATH):
        self.skills_dir = skills_dir
        self.skills: List[Dict[str, Any]] = []

    def scan_skills(self):
        """Scan the skills directory and parse SKILL.md frontmatter."""
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        self.skills = []
        for skill_name in os.listdir(self.skills_dir):
            if skill_name.startswith("."):
                continue
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                md_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(md_file):
                    try:
                        with open(md_file, "r") as f:
                            content = f.read()
                            if content.startswith("---"):
                                parts = content.split("---")
                                if len(parts) >= 3:
                                    frontmatter = parts[1]
                                    data = yaml.safe_load(frontmatter)
                                    data["name"] = data.get("name", skill_name)
                                    data["path"] = skill_path
                                    self.skills.append(data)
                    except Exception as e:
                        logger.error(f"Error parsing skill {skill_name}: {e}")

    def get_skill_names(self) -> List[str]:
        """Return a list of available skill names."""
        return [s["name"] for s in self.skills]

    def get_skill_descriptions(self) -> str:
        """Format skill list for LLM context."""
        if not self.skills:
            return "No specialized agents currently available."
        
        lines = ["AVAILABLE SPECIALIZED AGENTS:"]
        for s in self.skills:
            lines.append(f"- **{s['name']}**: {s.get('description', 'No description available.')}")
        return "\n".join(lines)

    def get_skill_tools(self) -> List[Dict[str, Any]]:
        """Expose a 'use_skill' tool to Gemini."""
        skill_list = self.get_skill_names()
        # Cap the list for the tool description if it's too long
        display_list = skill_list[:50]
        
        return [
            {
                "name": "hire_specialized_agent",
                "description": f"Hire a specialized agent with a specific skill set to handle a complex task. Available skills include: {', '.join(display_list)}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "The name of the skill to use.",
                            "enum": skill_list if len(skill_list) < 250 else None # Don't blow up tool spec
                        },
                        "task_description": {
                            "type": "string",
                            "description": "A detailed description of the task for the specialized agent. Include all necessary context."
                        }
                    },
                    "required": ["skill_name", "task_description"]
                }
            }
        ]

# Global instance
skill_manager = SkillManager()
