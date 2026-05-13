import os
import json
import logging
import asyncio
from typing import List, Dict, Optional
from .memory import memory_manager
from .context import IGNORED_DIRS, read_file_safe, CLIENTLY_ROOT

logger = logging.getLogger(__name__)

class RepositoryIndexer:
    def __init__(self):
        self.is_indexing = False
        self.progress = 0
        self.total_files = 0
        self.current_file = ""

    async def index_repository(self, path: str):
        """
        Recursively scan the repository, summarize files, and store in memory.
        """
        if self.is_indexing:
            return
        
        self.is_indexing = True
        self.progress = 0
        self.current_file = "Scanning..."
        
        try:
            files_to_index = []
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                for file in files:
                    if file.startswith("."):
                        continue
                    ext = os.path.splitext(file)[1].lower()
                    if ext in [".py", ".swift", ".js", ".ts", ".tsx", ".json", ".md", ".txt", ".rs", ".go", ".c", ".h", ".cpp"]:
                        files_to_index.append(os.path.join(root, file))
            
            self.total_files = len(files_to_index)
            logger.info(f"Starting repository indexing: {self.total_files} files found.")
            
            for i, file_path in enumerate(files_to_index):
                self.current_file = os.path.relpath(file_path, path)
                self.progress = int(((i + 1) / self.total_files) * 100)
                
                # Read content
                content = read_file_safe(file_path, max_chars=8000)
                if not content:
                    continue
                
                # Generate summary via LLM (architectural perspective)
                from .llm import call_gemini
                summary_prompt = f"""Analyze the following file from the project: {self.current_file}
                
                CONTENT:
                {content}
                
                Summarize the architectural purpose, key functions/classes, and its role in the project.
                Be concise but precise. Focus on technical importance."""
                
                summary = call_gemini(summary_prompt, "You are a Repository Indexer Assistant.", model="gemini-2.5-flash", temperature=0.1)
                
                # Add to memory
                memory_manager.add_memory(
                    content=f"FILE: {self.current_file}\\nARCHITECTURAL SUMMARY:\\n{summary}",
                    meta={
                        "type": "repo_index",
                        "file_path": self.current_file,
                        "project_root": path,
                        "timestamp": os.path.getmtime(file_path)
                    }
                )
                
                # Throttle to avoid rate limits
                await asyncio.sleep(0.5)
                
            self.current_file = "Indexing Complete"
            logger.info("Repository indexing complete.")
            
        except Exception as e:
            logger.error(f"Indexing error: {e}")
            self.current_file = f"Error: {e}"
        finally:
            self.is_indexing = False

repo_indexer = RepositoryIndexer()
