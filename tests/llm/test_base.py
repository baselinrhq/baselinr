"""Tests for LLM base classes."""

import pytest

from baselinr.llm.base import LLMConfigError, LLMProvider, LLMResponse


def test_llm_response():
    """Test LLMResponse dataclass."""
    response = LLMResponse(
        text="Test explanation",
        model="gpt-4o-mini",
        provider="openai",
        tokens_used=100,
        cost_usd=0.001,
        latency_ms=500.0,
    )

    assert response.text == "Test explanation"
    assert response.model == "gpt-4o-mini"
    assert response.provider == "openai"
    assert response.tokens_used == 100
    assert response.cost_usd == 0.001
    assert response.latency_ms == 500.0


def test_llm_provider_abstract():
    """Test that LLMProvider is abstract and cannot be instantiated."""
    with pytest.raises(TypeError):
        LLMProvider(None)  # type: ignore


def test_llm_exceptions():
    """Test LLM exception classes."""
    api_error = LLMConfigError("Test error")
    assert str(api_error) == "Test error"

