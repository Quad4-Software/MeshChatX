"""Configuration module for LXMFy."""

import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    """Configuration settings for LXMFBot.

    Attributes:
        name (str): The name of the bot. Defaults to "LXMFBot".
        announce (int): The announce interval in seconds. Defaults to 600.
        announce_immediately (bool): Whether to announce immediately on startup. Defaults to True.
        admins (set): A set of admin identity hashes. Defaults to an empty set.
        hot_reloading (bool): Whether to enable hot reloading of cogs. Defaults to False.
        rate_limit (int): The maximum number of messages allowed per cooldown period. Defaults to 5.
        cooldown (int): The cooldown period in seconds. Defaults to 60.
        max_warnings (int): The maximum number of spam warnings before action is taken. Defaults to 3.
        warning_timeout (int): The duration in seconds for which a spam warning is active. Defaults to 300.
        command_prefix (str): The prefix for bot commands. Defaults to "/".
        cogs_dir (str): The directory to load cogs from. Defaults to "cogs".
        cogs_enabled (bool): Whether to enable cogs. Defaults to True.
        permissions_enabled (bool): Whether to enable the permission system. Defaults to False.
        storage_type (str): The type of storage to use ("json" or "sqlite"). Defaults to "json".
        storage_path (str): The path to the storage file or directory. Defaults to "data".
        first_message_enabled (bool): Whether to enable first message handling. Defaults to True.
        event_logging_enabled (bool): Whether to enable event logging. Defaults to True.
        max_logged_events (int): The maximum number of events to log. Defaults to 1000.
        event_middleware_enabled (bool): Whether to enable event middleware. Defaults to True.
        announce_enabled (bool): Whether to enable bot announcements. Defaults to True.
        signature_verification_enabled (bool): Whether to enable cryptographic signature verification for incoming messages. Defaults to False.
        require_message_signatures (bool): Whether to reject unsigned messages when signature verification is enabled. Defaults to False.
        require_stamps (bool): Whether to reject messages with invalid stamps. Defaults to False.
        request_unknown_identities (bool): Whether to request unknown identities from the network when a message is received from an unknown source. Defaults to False.
        stamp_cost (int): The cost of stamps for messages. If set, required for incoming and applied to outgoing. None disables stamps. Defaults to None.
        direct_delivery_retries (int): Number of times to retry direct delivery before falling back to propagation. Defaults to 3.
        propagation_fallback_enabled (bool): Whether to use propagation nodes as fallback after direct delivery fails. Defaults to True.
        propagation_node (str): The destination hash of the outbound propagation node. If None and autopeer_propagation is True, automatically discovers nodes. Defaults to None.
        autopeer_propagation (bool): Whether to automatically discover and peer with propagation nodes from announces. Defaults to False.
        autopeer_maxdepth (int): Maximum hop depth for auto-peering with propagation nodes. None = no limit. Defaults to 4.
        enable_propagation_node (bool): Whether to run this bot as a propagation node. Defaults to False.
        message_storage_limit_mb (float): Maximum storage for propagation node messages in megabytes. Only applies when enable_propagation_node is True. Defaults to 500 MB.
        config_path (str): The path to the bot configuration directory. If None, defaults to "config" in the current working directory. Defaults to None.
        reticulum_config_dir (str): The Reticulum config directory used for RNS shared instance/auth state. If None, falls back to config_path. Can also be set via LXMFY_RETICULUM_CONFIG_DIR.
        test_mode (bool): Whether to run in test mode (skips RNS initialization). Defaults to False.
        announce_display_name_file (str): Optional filename under config_path whose UTF-8 contents override the bot display name for LXMF delivery announces. If unset, ``bot_display_name.txt`` is read when present. Otherwise ``name`` is used.

    """

    name: str = "LXMFBot"
    announce: int = 600
    announce_immediately: bool = True
    admins: set = None
    hot_reloading: bool = False
    rate_limit: int = 5
    cooldown: int = 60
    max_warnings: int = 3
    warning_timeout: int = 300
    command_prefix: str = "/"
    cogs_dir: str = "cogs"
    cogs_enabled: bool = True
    permissions_enabled: bool = False
    storage_type: str = "json"
    storage_path: str = "data"
    first_message_enabled: bool = True
    event_logging_enabled: bool = True
    max_logged_events: int = 1000
    event_middleware_enabled: bool = True
    announce_enabled: bool = True
    signature_verification_enabled: bool = False
    require_message_signatures: bool = False
    require_stamps: bool = False
    request_unknown_identities: bool = False
    stamp_cost: int = None
    direct_delivery_retries: int = 3
    propagation_fallback_enabled: bool = True
    propagation_node: str = None
    autopeer_propagation: bool = False
    autopeer_maxdepth: int = 4
    enable_propagation_node: bool = False
    message_storage_limit_mb: float = 500.0
    config_path: str = None
    reticulum_config_dir: str = None
    announce_display_name_file: str = None
    test_mode: bool = False
    identity_pinning_enabled: bool = False
    message_persistence_enabled: bool = False
    dynamic_cogs_enabled: bool = True
    external_cogs_enabled: bool = True
    external_cogs_sandbox_enabled: bool = True
    external_cogs_sandbox_type: str = "auto"  # 'auto', 'bwrap', 'firejail', 'none'
    external_cogs_timeout: int = 30
    nlp_enabled: bool = False
    nlp_threshold: float = 0.5
    link_support_enabled: bool = False
    opportunistic_sending: bool = True

    def __post_init__(self):
        """Post-initialization to ensure admins is a set."""
        if self.admins is None:
            self.admins = set()
        if self.reticulum_config_dir is None:
            self.reticulum_config_dir = os.environ.get("LXMFY_RETICULUM_CONFIG_DIR")

    def __str__(self):
        """Return a string representation of the BotConfig object."""
        return f"BotConfig(name={self.name}, announce={self.announce}, announce_immediately={self.announce_immediately}, admins={self.admins}, hot_reloading={self.hot_reloading}, rate_limit={self.rate_limit}, cooldown={self.cooldown}, max_warnings={self.max_warnings}, warning_timeout={self.warning_timeout}, command_prefix={self.command_prefix}, cogs_dir={self.cogs_dir}, cogs_enabled={self.cogs_enabled}, permissions_enabled={self.permissions_enabled}, storage_type={self.storage_type}, storage_path={self.storage_path}, first_message_enabled={self.first_message_enabled}, event_logging_enabled={self.event_logging_enabled}, max_logged_events={self.max_logged_events}, event_middleware_enabled={self.event_middleware_enabled}, announce_enabled={self.announce_enabled}, signature_verification_enabled={self.signature_verification_enabled}, require_message_signatures={self.require_message_signatures}, require_stamps={self.require_stamps}, request_unknown_identities={self.request_unknown_identities}, stamp_cost={self.stamp_cost}, test_mode={self.test_mode}, identity_pinning_enabled={self.identity_pinning_enabled}, message_persistence_enabled={self.message_persistence_enabled}, dynamic_cogs_enabled={self.dynamic_cogs_enabled})"
