"""
LLM module for Baselinr.

Provides human-readable explanations for alerts using BYOK (Bring Your Own Key)
LLM providers including OpenAI, Anthropic, Azure OpenAI, and Ollama.
"""

from .explainer import LLMExplainer

__all__ = ["LLMExplainer"]
