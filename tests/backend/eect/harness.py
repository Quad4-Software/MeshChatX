# SPDX-License-Identifier: 0BSD
"""Seeded harness and failure banner for EECT scenarios."""

from __future__ import annotations

import os
import random
from collections.abc import Iterator
from contextlib import contextmanager

from tests.backend.eect.catalog import Scenario, get_scenario


def resolve_seed(explicit: int | None = None) -> int:
    """Return replay seed from arg, MESHCHAT_EECT_SEED, or a fresh random seed."""
    if explicit is not None:
        return int(explicit) & 0xFFFFFFFF
    raw = os.environ.get("MESHCHAT_EECT_SEED")
    if raw is not None and str(raw).strip() != "":
        return int(str(raw).strip(), 0) & 0xFFFFFFFF
    return random.SystemRandom().randint(0, 0xFFFFFFFF)


def format_failure_banner(scenario: Scenario, seed: int, detail: str = "") -> str:
    lines = [
        "EECT FAILURE",
        f"  scenario_id: {scenario.id}",
        f"  pack:        {scenario.pack}",
        f"  gate:        {scenario.gate}",
        f"  taxonomy:    {scenario.taxonomy}",
        f"  seed:        {seed}",
        f"  replay:      MESHCHAT_EECT_SEED={seed}",
    ]
    if detail:
        lines.append(f"  detail:      {detail}")
    return "\n".join(lines)


@contextmanager
def eect_scenario(
    scenario_id: str,
    seed: int | None = None,
) -> Iterator[tuple[Scenario, int, random.Random]]:
    """Bind scenario + seeded RNG. On assert failure, append banner to the message."""
    scenario = get_scenario(scenario_id)
    resolved = resolve_seed(seed)
    rng = random.Random(resolved)
    try:
        yield scenario, resolved, rng
    except AssertionError as exc:
        banner = format_failure_banner(scenario, resolved, detail=str(exc))
        raise AssertionError(f"{banner}\n\n{exc}") from None
