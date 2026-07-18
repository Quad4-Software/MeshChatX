# SPDX-License-Identifier: 0BSD
"""Scenario registry for Extended Edge Case Tester packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Taxonomy = Literal[
    "logic",
    "timing",
    "identity_leak",
    "security_surface",
    "resource",
    "live_env",
]


@dataclass(frozen=True)
class Scenario:
    """One EECT scenario mapped to a Zen gate and failure taxonomy."""

    id: str
    pack: str
    gate: str
    taxonomy: Taxonomy
    summary: str
    ci: bool = True


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="identity.switch.teardown_clears_context",
        pack="IdentitySwitchPack",
        gate="gate6-identity-context",
        taxonomy="identity_leak",
        summary="hotswap tears down prior context and drops it from contexts map",
    ),
    Scenario(
        id="identity.switch.storage_paths_isolated",
        pack="IdentitySwitchPack",
        gate="gate6-identity-context",
        taxonomy="identity_leak",
        summary="identity A and B use distinct database.db paths under identities/",
    ),
    Scenario(
        id="path.direct.blocks_when_unavailable",
        pack="MissingPathPack",
        gate="gate4-scarcity-async",
        taxonomy="timing",
        summary="direct send raises recoverable TimeoutError and never outbound",
    ),
    Scenario(
        id="path.propagated.skips_await",
        pack="MissingPathPack",
        gate="gate4-scarcity-async",
        taxonomy="timing",
        summary="propagated delivery does not await peer path",
    ),
    Scenario(
        id="hostile.favourites.layout_fuzz",
        pack="HostileMediumPack",
        gate="gate3-hostile-medium",
        taxonomy="security_surface",
        summary="normalize_favourites_layout never crashes on hostile blobs",
    ),
    Scenario(
        id="hostile.bug_report.redacts_secrets",
        pack="HostileMediumPack",
        gate="gate3-hostile-medium",
        taxonomy="security_surface",
        summary="bug report preview redacts paths and full destination hashes",
    ),
    Scenario(
        id="hostile.overlay.format_char_fixed",
        pack="HostileMediumPack",
        gate="gate3-hostile-medium",
        taxonomy="security_surface",
        summary="Micron/Nomad strip fixed even when hidden with ZWSP or soft hyphen",
    ),
    Scenario(
        id="hostile.favourites.null_bytes",
        pack="HostileMediumPack",
        gate="gate3-hostile-medium",
        taxonomy="security_surface",
        summary="favourites layout rejects NUL in section ids and hashes",
    ),
    Scenario(
        id="hostile.url.decimal_link_local",
        pack="HostileMediumPack",
        gate="gate3-hostile-medium",
        taxonomy="security_surface",
        summary="LibreTranslate URL guard rejects decimal/hex link-local SSRF forms",
    ),
    Scenario(
        id="scarcity.conversation.preview_capped",
        pack="ScarcityPack",
        gate="gate4-scarcity-async",
        taxonomy="resource",
        summary="conversation list content preview stays within 240 chars",
    ),
    Scenario(
        id="scarcity.conversation.fields_slim",
        pack="ScarcityPack",
        gate="gate4-scarcity-async",
        taxonomy="resource",
        summary="conversation list omits heavy fields blobs",
    ),
    Scenario(
        id="auth.csrf.mutating_without_token",
        pack="AuthSurfacePack",
        gate="gate6-auth-surface",
        taxonomy="security_surface",
        summary="sampled mutating HTTP routes reject missing CSRF",
    ),
    Scenario(
        id="auth.csrf.mutating_with_token",
        pack="AuthSurfacePack",
        gate="gate6-auth-surface",
        taxonomy="security_surface",
        summary="sampled mutating HTTP routes accept valid CSRF",
    ),
    Scenario(
        id="lv.l0.imports_sqlite_unicode",
        pack="LiveValidation",
        gate="gate0-intent",
        taxonomy="live_env",
        summary="L0 self-check imports, sqlite, unicode path",
    ),
    Scenario(
        id="lv.l1.status_and_csrf_reject",
        pack="LiveValidation",
        gate="gate6-auth-surface",
        taxonomy="live_env",
        summary="L1 status OK and unauth mutating POST rejected",
    ),
    Scenario(
        id="lv.l2.rns_subprocess",
        pack="LiveValidation",
        gate="gate0-intent",
        taxonomy="live_env",
        summary="L2 RNS start/exit in isolated subprocess",
        ci=False,
    ),
    Scenario(
        id="lv.l3.loopback_tcp",
        pack="LiveValidation",
        gate="gate0-intent",
        taxonomy="live_env",
        summary="L3 loopback TCP bind prove-alive",
        ci=False,
    ),
)


def get_scenario(scenario_id: str) -> Scenario:
    for scenario in SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"unknown EECT scenario: {scenario_id}")


def scenarios_for_pack(pack: str) -> tuple[Scenario, ...]:
    return tuple(s for s in SCENARIOS if s.pack == pack)
