"""
Neo v2 — Context Engine
Repository scanning, git analysis, config parsing, workspace indexing.
"""

import os
import subprocess
from typing import Optional


CLIENTLY_ROOT = "/Users/albin/Documents/cliently"
ANTIGRAVITY_ROOT = os.path.expanduser("~/.gemini/antigravity")

IGNORED_DIRS = {
    "node_modules", "__pycache__", ".next", ".git", "build", "dist",
    "Derived", ".DS_Store", ".turbo", "coverage", ".venv",
}

CONFIG_FILES = [
    "package.json", "tsconfig.json", "next.config.ts",
    "prisma/schema.prisma", "Cargo.toml", "tauri.conf.json",
    "pyproject.toml", "Project.swift",
]


def get_directory_tree(path: str, depth: int = 3, prefix: str = "") -> str:
    if depth <= 0 or not os.path.isdir(path):
        return ""
    try:
        items = sorted(os.listdir(path))
        items = [i for i in items if i not in IGNORED_DIRS and not i.startswith(".")]
        lines = []
        for i, item in enumerate(items[:25]):
            full = os.path.join(path, item)
            is_last = i == len(items[:25]) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{item}")
            if os.path.isdir(full) and depth > 1:
                ext = "    " if is_last else "│   "
                sub = get_directory_tree(full, depth - 1, prefix + ext)
                if sub:
                    lines.append(sub)
        return "\n".join(lines)
    except Exception:
        return ""


def read_file_safe(path: str, max_chars: int = 6000) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:max_chars]
    except Exception:
        return None


def get_git_status() -> str:
    try:
        res = subprocess.run(
            ["git", "status", "-s"], cwd=CLIENTLY_ROOT,
            capture_output=True, text=True, timeout=5
        )
        return res.stdout.strip() or "Working tree clean."
    except Exception:
        return "Git unavailable."


def get_git_log(n: int = 5) -> str:
    try:
        res = subprocess.run(
            ["git", "log", "-n", str(n), "--oneline"], cwd=CLIENTLY_ROOT,
            capture_output=True, text=True, timeout=5
        )
        return res.stdout.strip()
    except Exception:
        return "Git log unavailable."


def get_git_branch() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=CLIENTLY_ROOT,
            capture_output=True, text=True, timeout=5
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_workspace_context() -> str:
    parts = []
    branch = get_git_branch()
    status = get_git_status()
    log = get_git_log()
    parts.append(f"**Branch:** `{branch}`")
    parts.append(f"**Git Status:**\n```\n{status}\n```")
    parts.append(f"**Recent Commits:**\n```\n{log}\n```")
    return "\n\n".join(parts)


def gather_file_context(prompt: str) -> str:
    prompt_lower = prompt.lower()
    context_parts = []
    target_dirs = []
    if "windows" in prompt_lower:
        target_dirs.append(os.path.join(CLIENTLY_ROOT, "cliently-windows"))
    if "mobile" in prompt_lower:
        target_dirs.append(os.path.join(CLIENTLY_ROOT, "cliently-mobile"))
    if "neo" in prompt_lower:
        target_dirs.append(os.path.join(CLIENTLY_ROOT, "Neo"))
    if not target_dirs:
        target_dirs.append(CLIENTLY_ROOT)

    for target_dir in target_dirs:
        if not os.path.exists(target_dir):
            continue
        for cfg in CONFIG_FILES:
            cfg_path = os.path.join(target_dir, cfg)
            content = read_file_safe(cfg_path)
            if content:
                rel = os.path.relpath(cfg_path, CLIENTLY_ROOT)
                context_parts.append(f"**{rel}:**\n```\n{content}\n```")

    return "\n\n".join(context_parts[:15])


def get_constitution() -> str:
    path = os.path.join(CLIENTLY_ROOT, "Neo", "constitution.md")
    return read_file_safe(path, max_chars=4000) or "No constitution file found."


def list_antigravity_skills(limit: int = 40) -> list[str]:
    try:
        skills_dir = os.path.join(ANTIGRAVITY_ROOT, "skills")
        if os.path.exists(skills_dir):
            skills = sorted(os.listdir(skills_dir))
            return [s for s in skills if not s.startswith(".")][:limit]
    except Exception:
        pass
    return []


def list_mcp_servers() -> list[str]:
    from .mcp_manager import mcp_manager
    return list(mcp_manager.servers.keys())
