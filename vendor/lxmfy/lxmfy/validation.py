"""Validation module for LXMFy configuration and best practices."""

import logging
from dataclasses import dataclass
from typing import Any

from .storage import JSONStorage

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        valid (bool): Indicates whether the validation was successful.
        messages (list[str]): A list of messages associated with the validation result.
        severity (str): The severity level of the validation result ('error', 'warning', or 'info').

    """

    valid: bool
    messages: list[str]
    severity: str


class ConfigValidator:
    """Validates bot configuration settings."""

    @staticmethod
    def validate_config(config: Any) -> list[ValidationResult]:
        """Validate the given bot configuration.

        Args:
            config (Any): The bot configuration object to validate.

        Returns:
            list[ValidationResult]: A list of validation results.

        """
        results = []

        try:
            if len(getattr(config, "name", "")) < 3:
                results.append(
                    ValidationResult(
                        False,
                        ["Bot name should be at least 3 characters long"],
                        "error",
                    ),
                )

            announce = getattr(config, "announce", 0)
            if 0 < announce < 300:
                results.append(
                    ValidationResult(
                        False,
                        [
                            "Announce interval should be at least 300 seconds to avoid network spam",
                        ],
                        "warning",
                    ),
                )

            if getattr(config, "rate_limit", 0) > 10:
                results.append(
                    ValidationResult(
                        False,
                        [
                            "Rate limit above 10 messages per minute may be too permissive",
                        ],
                        "warning",
                    ),
                )

            if getattr(config, "cooldown", 0) < 30:
                results.append(
                    ValidationResult(
                        False,
                        ["Cooldown period should be at least 30 seconds"],
                        "warning",
                    ),
                )

        except Exception as e:
            logger.error("Error during config validation: %s", str(e))
            results.append(
                ValidationResult(
                    False,
                    [f"Error validating configuration: {e!s}"],
                    "error",
                ),
            )

        return results


class BestPracticesChecker:
    """Checks for bot implementation best practices."""

    @staticmethod
    def check_bot(bot: Any) -> list[ValidationResult]:
        """Check the bot instance for best practices.

        Args:
            bot (Any): The bot instance to check.

        Returns:
            list[ValidationResult]: A list of validation results.

        """
        results = []

        if not getattr(bot.config, "permissions_enabled", False):
            results.append(
                ValidationResult(
                    False,
                    [
                        "Permission system is disabled. Consider enabling it for better security",
                    ],
                    "warning",
                ),
            )

        if getattr(bot, "command_prefix", None) is None:
            results.append(
                ValidationResult(
                    False,
                    ["Using no command prefix may cause high processing overhead"],
                    "warning",
                ),
            )

        if not getattr(bot, "admins", None):
            results.append(
                ValidationResult(
                    False,
                    ["No admin users configured. Bot management will be limited"],
                    "warning",
                ),
            )

        if getattr(bot.config, "storage_type", "") == "json":
            results.append(
                ValidationResult(
                    True,
                    [
                        "Consider using SQLite storage for better performance with large datasets",
                    ],
                    "info",
                ),
            )

        sig_enabled = getattr(bot.config, "signature_verification_enabled", False)
        sig_required = getattr(bot.config, "require_message_signatures", False)

        if sig_enabled and sig_required:
            results.append(
                ValidationResult(
                    True,
                    [
                        "Strict signature verification enabled - all messages must be signed",
                    ],
                    "info",
                ),
            )
        elif sig_enabled and not sig_required:
            results.append(
                ValidationResult(
                    True,
                    [
                        "Signature verification enabled but not required - unsigned messages will be logged",
                    ],
                    "info",
                ),
            )
        elif not sig_enabled:
            results.append(
                ValidationResult(
                    False,
                    [
                        "Signature verification is disabled. Consider enabling it for enhanced security",
                    ],
                    "warning",
                ),
            )

        return results


class PerformanceAnalyzer:
    """Analyzes bot configuration for performance optimization opportunities."""

    @staticmethod
    def analyze_bot(bot: Any) -> list[ValidationResult]:
        """Analyze the bot instance for performance optimization opportunities.

        Args:
            bot (Any): The bot instance to analyze.

        Returns:
            list[ValidationResult]: A list of validation results.

        """
        results = []

        if not hasattr(bot, "transport") or not hasattr(bot.transport, "cached_links"):
            results.append(
                ValidationResult(
                    False,
                    ["Link caching is not enabled. This may impact performance"],
                    "warning",
                ),
            )

        if hasattr(bot, "queue") and getattr(bot.queue, "maxsize", 0) < 10:
            results.append(
                ValidationResult(
                    False,
                    ["Consider increasing queue size for better message handling"],
                    "info",
                ),
            )

        if (
            hasattr(bot, "storage")
            and hasattr(bot.storage, "backend")
            and isinstance(bot.storage.backend, JSONStorage)
        ):
            results.append(
                ValidationResult(
                    True,
                    [
                        "SQLite backend recommended for better performance with large datasets",
                    ],
                    "info",
                ),
            )

        return results


def validate_bot(bot: Any) -> dict[str, list[ValidationResult]]:
    """Run all validation checks on a bot instance.

    Args:
        bot (Any): The bot instance to validate.

    Returns:
        dict[str, list[ValidationResult]]: A dictionary containing validation results for different categories.

    """
    try:
        return {
            "config": ConfigValidator.validate_config(bot.config),
            "best_practices": BestPracticesChecker.check_bot(bot),
            "performance": PerformanceAnalyzer.analyze_bot(bot),
        }
    except Exception as e:
        logger.error("Validation error: %s", str(e))
        return {
            "error": [
                ValidationResult(
                    False,
                    [f"Error during validation: {e!s}"],
                    "error",
                ),
            ],
        }


def format_validation_results(results: dict[str, list[ValidationResult]]) -> str:
    """Format validation results into a readable string.

    Args:
        results (dict[str, list[ValidationResult]]): A dictionary containing validation results.

    Returns:
        str: A formatted string representing the validation results.

    """
    output = []

    for category, checks in results.items():
        output.append(f"\n=== {category.upper()} ===")
        for result in checks:
            prefix = (
                "[ERROR]"
                if not result.valid and result.severity == "error"
                else "[WARNING]"
                if result.severity == "warning"
                else "[INFO]"
            )
            output.extend(f"{prefix} {msg}" for msg in result.messages)

    return "\n".join(output)
