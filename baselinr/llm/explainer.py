"""
Main LLM explainer orchestration class.

Handles LLM provider initialization, prompt construction, and graceful
fallback to template-based explanations.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ..config.schema import LLMConfig

from .base import LLMAPIError, LLMConfigError, LLMProvider, LLMTimeoutError
from .prompts import (
    construct_anomaly_prompt,
    construct_drift_prompt,
    construct_schema_change_prompt,
    get_system_prompt,
)
from .templates import (
    generate_anomaly_explanation,
    generate_drift_explanation,
    generate_schema_change_explanation,
)

logger = logging.getLogger(__name__)


class LLMExplainer:
    """
    Main orchestration class for generating LLM-powered explanations.

    Handles provider initialization, prompt construction, and fallback
    to template-based explanations when LLM is unavailable.
    """

    def __init__(self, config: Optional["LLMConfig"] = None):
        """
        Initialize LLM explainer.

        Args:
            config: LLM configuration (if None, LLM features are disabled)
        """
        self.config = config
        self.provider: Optional[LLMProvider] = None
        self.logger = logging.getLogger(__name__)

        # Initialize provider if LLM is enabled
        if config and config.enabled:
            try:
                from .providers.factory import create_provider

                self.provider = create_provider(config)
                self.logger.info(f"Initialized LLM provider: {config.provider}")
            except LLMConfigError as e:
                self.logger.warning(
                    f"Failed to initialize LLM provider: {e}. Falling back to templates."
                )
                self.provider = None
            except Exception as e:
                self.logger.warning(
                    f"Unexpected error initializing LLM provider: {e}. Falling back to templates."
                )
                self.provider = None

    def generate_explanation(
        self,
        alert_data: Dict[str, Any],
        alert_type: str = "drift",
        fallback_object: Optional[Any] = None,
    ) -> str:
        """
        Generate explanation for an alert with fallback chain.

        Args:
            alert_data: Dictionary containing alert details
            alert_type: Type of alert ("drift", "anomaly", "schema_change")
            fallback_object: Optional object for template fallback
                (ColumnDrift, AnomalyResult, or change string)

        Returns:
            Human-readable explanation string
        """
        # Try LLM if enabled and provider is available
        if self.config and self.config.enabled and self.provider:
            try:
                return self._generate_llm_explanation(alert_data, alert_type)
            except (LLMAPIError, LLMTimeoutError, LLMConfigError) as e:
                self.logger.warning(f"LLM explanation failed: {e}. Falling back to template.")
            except Exception as e:
                self.logger.warning(
                    f"Unexpected error in LLM explanation: {e}. Falling back to template."
                )

        # Fall back to template-based explanation
        return self._generate_template_explanation(alert_data, alert_type, fallback_object)

    def _generate_llm_explanation(self, alert_data: Dict[str, Any], alert_type: str) -> str:
        """
        Generate explanation using LLM.

        Args:
            alert_data: Dictionary containing alert details
            alert_type: Type of alert

        Returns:
            LLM-generated explanation

        Raises:
            LLMAPIError: If LLM call fails
            LLMTimeoutError: If request times out
        """
        if not self.provider:
            raise LLMConfigError("LLM provider not initialized")

        # Construct prompt based on alert type
        if alert_type == "drift":
            prompt = construct_drift_prompt(alert_data)
        elif alert_type == "anomaly":
            prompt = construct_anomaly_prompt(alert_data)
        elif alert_type == "schema_change":
            prompt = construct_schema_change_prompt(alert_data)
        else:
            raise ValueError(f"Unknown alert type: {alert_type}")

        # Get system prompt
        system_prompt = get_system_prompt()

        # Generate explanation
        if self.config is None:
            raise LLMConfigError("LLM config is not set")
        response = self.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        self.logger.debug(
            f"Generated LLM explanation: {response.tokens_used} tokens, "
            f"{response.latency_ms:.0f}ms latency"
        )

        return response.text.strip()

    def _generate_template_explanation(
        self,
        alert_data: Dict[str, Any],
        alert_type: str,
        fallback_object: Optional[Any] = None,
    ) -> str:
        """
        Generate template-based explanation.

        Args:
            alert_data: Dictionary containing alert details
            alert_type: Type of alert
            fallback_object: Optional object for template generation

        Returns:
            Template-based explanation
        """
        if alert_type == "drift":
            if fallback_object:
                return generate_drift_explanation(fallback_object)
            # Try to construct from alert_data if no object provided
            from ..drift.detector import ColumnDrift

            drift = ColumnDrift(
                column_name=alert_data.get("column", "unknown"),
                metric_name=alert_data.get("metric", "unknown"),
                baseline_value=alert_data.get("baseline_value"),
                current_value=alert_data.get("current_value"),
                change_percent=alert_data.get("change_percent"),
                change_absolute=alert_data.get("change_absolute"),
                drift_detected=True,
                drift_severity=alert_data.get("drift_severity", "medium"),
                metadata={"table_name": alert_data.get("table", "unknown")},
            )
            return generate_drift_explanation(drift)

        elif alert_type == "anomaly":
            if fallback_object:
                return generate_anomaly_explanation(fallback_object)
            # Try to construct from alert_data if no object provided
            from ..anomaly.anomaly_types import AnomalyType
            from ..anomaly.detector import AnomalyResult

            anomaly = AnomalyResult(
                anomaly_type=AnomalyType.CONTROL_LIMIT_BREACH,  # Default
                table_name=alert_data.get("table", "unknown"),
                schema_name=alert_data.get("schema_name"),
                column_name=alert_data.get("column", "unknown"),
                metric_name=alert_data.get("metric", "unknown"),
                expected_value=alert_data.get("expected_value"),
                actual_value=alert_data.get("actual_value", 0.0),
                deviation_score=alert_data.get("deviation_score", 0.0),
                severity=alert_data.get("severity", "medium"),
                detection_method=alert_data.get("detection_method", "unknown"),
                metadata=alert_data.get("metadata", {}),
            )
            return generate_anomaly_explanation(anomaly)

        elif alert_type == "schema_change":
            change_str = alert_data.get(
                "change", str(fallback_object) if fallback_object else "Schema change detected"
            )
            return generate_schema_change_explanation(
                change=change_str,
                table=alert_data.get("table"),
                change_type=alert_data.get("change_type"),
                column=alert_data.get("column"),
            )

        else:
            return f"Alert detected: {alert_type}"
