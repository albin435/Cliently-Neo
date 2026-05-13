import os
import random
import logging
import json
from typing import Optional, List, Any, Union, Dict
from google import genai
from google.genai import types

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables early
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

class LLMClient:
    def __init__(self):
        self.keys: List[str] = []
        
        # Load up to 4 keys explicitly as requested
        for i in range(1, 5):
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if key and key not in self.keys:
                self.keys.append(key)
        
        # Also include the default GEMINI_API_KEY if present
        default_key = os.environ.get("GEMINI_API_KEY")
        if default_key and default_key not in self.keys:
            self.keys.append(default_key)
            
        self.current_key_idx = 0
        if not self.keys:
            self._client = None
            logger.warning("No Gemini API keys configured. LLM functions will fail.")
        else:
            self._client = genai.Client(api_key=self.keys[self.current_key_idx])
            
    def _rotate_key(self) -> bool:
        """Rotate to the next available API key. Returns False if no other keys are available."""
        if len(self.keys) <= 1:
            return False
            
        self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
        self._client = genai.Client(api_key=self.keys[self.current_key_idx])
        logger.info(f"Rotated to API Key #{self.current_key_idx + 1} of {len(self.keys)}")
        return True
        
    def generate_content(
        self, prompt: str, system: str, model: str = "gemini-2.0-flash", 
        temperature: float = 0.2, tools: Optional[List[Any]] = None,
        tool_handler: Optional[Any] = None,
        max_retries: int = 4
    ) -> str:
        """Call Gemini API with automatic key rotation and optional tool loop."""
        if not self._client:
            return "Error: GEMINI_API_KEY not configured."
            
        attempts = 0
        while attempts < max_retries:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                )
                if tools:
                    # Filter tools to be compatible with Gemini
                    gemini_tools = []
                    for t in tools:
                        gemini_tools.append(types.FunctionDeclaration(
                            name=t["name"],
                            description=t["description"],
                            parameters=t["parameters"]
                        ))
                    config.tools = [types.Tool(function_declarations=gemini_tools)]

                # Start a chat session for multi-turn tool calling
                chat = self._client.chats.create(model=model, config=config)
                response = chat.send_message(prompt)
                
                # Handle potential tool calling loop
                # The google-genai SDK handles automatic tool calling if functions are provided,
                # but we are doing it manually to have more control and avoid complex setup.
                
                # Check for tool calls
                while True:
                    tool_calls = []
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.function_call:
                                tool_calls.append(part.function_call)
                    
                    if not tool_calls:
                        break
                        
                    if not tool_handler:
                        logger.warning("Gemini requested tool call but no tool_handler provided.")
                        break

                    tool_responses = []
                    for call in tool_calls:
                        logger.info(f"Executing tool call: {call.name}")
                        result = tool_handler.execute_tool(call.name, call.args)
                        tool_responses.append(types.Part.from_function_response(
                            name=call.name,
                            response=result
                        ))
                    
                    # Send tool results back
                    response = chat.send_message(tool_responses)
                
                return response.text or ""
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                    logger.warning(f"Quota reached on key #{self.current_key_idx + 1}. Attempting rotation...")
                    rotated = self._rotate_key()
                    if not rotated:
                        return f"[QUOTA] Gemini API quota reached. Final error: {err}"
                    attempts += 1
                    continue
                return f"[ERROR] {err}"
                
        return "[QUOTA] All Gemini API keys exhausted their quotas."

    def embed_content(self, text: str, model: str = "text-embedding-004") -> Optional[List[float]]:
        """Generate embedding for text with automatic key rotation."""
        if not self._client or not text.strip():
            return None
            
        max_retries = min(4, max(1, len(self.keys)))
        attempts = 0
        while attempts < max_retries:
            try:
                response = self._client.models.embed_content(
                    model=model,
                    contents=text
                )
                if response.embeddings and len(response.embeddings) > 0:
                    return response.embeddings[0].values
                return None
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                    rotated = self._rotate_key()
                    if not rotated:
                        return None
                    attempts += 1
                    continue
                logger.error(f"Embedding error: {err}")
                return None
        return None

# Global instance
llm_client = LLMClient()

def call_gemini(
    prompt: str, system: str, model: str = "gemini-2.0-flash", 
    temperature: float = 0.2, tools: Optional[List[Any]] = None,
    tool_handler: Optional[Any] = None
) -> str:
    return llm_client.generate_content(prompt, system, model, temperature, tools=tools, tool_handler=tool_handler)

def _get_client():
    return llm_client._client
