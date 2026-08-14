---
name: exploratory-testing
description: Adversarial bug hunting with explicit hypotheses and oracle-backed confirmation. Use when the user asks to find bugs, fuzz a subsystem, or audit edge cases.
---

# Skill: exploratory-testing

Hunt bugs with explicit hypotheses and oracle-backed confirmation. Use when the user asks to find bugs, fuzz a subsystem, or audit edge cases beyond happy-path unit tests.

## When to use

- New or recently changed mesh protocols (RNS, LXMF, LXST, RRC)
- Security-sensitive surfaces (ACL, keys, auth, path handling, URL origin allowlists)
- After a feature lands and needs adversarial review
- Soft fuzz suites that need real oracles

## Method

1. Map the state machine or ACL matrix from code (not from memory alone).
2. Write 5 to 15 concrete hypotheses (Hn) with file references and predicted wrong behaviour.
3. For each high-priority hypothesis, write a failing oracle test first when possible.
4. Confirm with a focused pytest or vitest run. Fix only confirmed bugs unless asked to report only.
5. Record intentional behaviours (example IRC-style outside messages without +n) instead of changing them by accident.

## Hypothesis quality

Good:

- Non-member PART fans PARTED to real members (server.py _handle_part)
- Kick ERROR leaves client still in hub.rooms (manager.py _handle_error)

Bad:

- Maybe something is wrong with chat
- Fuzz random bytes and ensure no crash

## Priority order for mesh hubs and clients

1. ACL ordering (founder/op promotion before +k / +i)
2. Membership lies (phantom JOIN/PART, kick without peer notify)
3. Client/hub desync on ERROR
4. Persistence roundtrips (TOML, CBOR history, encrypted keys)
5. Rate limits and DoS stuck states
6. Cross-identity leakage

## Deliverable shape

When reporting to the user:

- Confirmed bugs (fixed or still open)
- Oracle tests added
- Intentional behaviours left alone
- Remaining hypotheses not yet tested

## Related

- `.agents/skills/test-oracles/SKILL.md`
- `.agents/skills/rrc-relay-chat/SKILL.md`
- `.agents/skills/reticulum-design-gates/SKILL.md`
- `.agents/skills/url-origin-allowlists/SKILL.md`
- `.agents/conventions/tests.md`
