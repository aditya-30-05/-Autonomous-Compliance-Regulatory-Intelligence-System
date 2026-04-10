"""
utils/llm_client.py
─────────────────────────────────────────────────────────────────────────────
Unified LLM client factory.
  • Default: OpenAI (GPT-4o-mini or configured model)
  • Fallback: Ollama (local)

Usage:
    from utils.llm_client import get_llm_client, build_prompt
    llm = get_llm_client()
    result = llm.invoke("Your prompt here")
─────────────────────────────────────────────────────────────────────────────
"""

import os
from string import Template

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER   = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_KEY     = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3")


def get_llm_client():
    """
    Returns a LangChain LLM instance based on LLM_PROVIDER env var.
    Falls back to Ollama if OpenAI key is missing.
    """
    if LLM_PROVIDER == "ollama":
        from langchain_community.llms import Ollama
        print("[LLMClient] Using Ollama →", OLLAMA_MODEL)
        return Ollama(base_url=OLLAMA_URL, model=OLLAMA_MODEL)

    if not OPENAI_KEY or OPENAI_KEY.startswith("sk-your"):
        # Graceful fallback → Ollama
        try:
            from langchain_community.llms import Ollama
            print("[LLMClient] ⚠️  No valid OpenAI key — falling back to Ollama")
            return Ollama(base_url=OLLAMA_URL, model=OLLAMA_MODEL)
        except Exception:
            raise EnvironmentError(
                "No LLM available. Set OPENAI_API_KEY or start an Ollama server."
            )

    from langchain_openai import ChatOpenAI
    print(f"[LLMClient] Using OpenAI → {OPENAI_MODEL}")
    return ChatOpenAI(
        api_key=OPENAI_KEY,
        model=OPENAI_MODEL,
        temperature=0.3,
        max_tokens=1024,
    )


def build_prompt(template: str, variables: dict) -> str:
    """
    Simple $-style string substitution for prompt templates.
    Keys in 'variables' replace ${key} or $key placeholders.
    """
    for key, val in variables.items():
        template = template.replace("{" + key + "}", str(val))
    return template
