---
name: test-oracles
description: Property, fuzz, and security tests that accept or reject with an independent oracle. Use when adding Hypothesis tests or reviewing soft fuzz.
---

# Skill: test-oracles

Write property, fuzz, and security tests that decide accept or reject with an independent oracle. Never soft-fuzz that only checks nothing crashed.

## When to use

- Adding Hypothesis or randomized tests
- Security or ACL coverage (auth, room keys, path jail, CSRF)
- Protocol decode/encode, parsers, normalizers
- Reviewing tests that look like fuzz but assert nothing

## What an oracle is

An oracle predicts the correct outcome from the input alone (or from a simpler trusted model), then the test checks the code matches that prediction.

| Oracle type    | Example                                     |
| -------------- | ------------------------------------------- |
| Accept/reject  | Empty room name must raise ValueError       |
| Round-trip     | encode(decode(x)) == x when decode succeeds |
| Jail           | Successful path stays under storage root    |
| Closed reasons | Error message is one of a fixed set         |
| Membership     | After PART by non-member, no PARTED fanout  |

## Hard refuse (soft fuzz)

Do not ship tests that only do:

- try/except pass around the unit under test
- assert that a call did not raise, with no postcondition
- assert response has key ok without checking True or False
- mocks that always succeed under a security check

## Workflow

1. State the invariant in one sentence.
2. Build inputs (Hypothesis strategy or explicit adversarial cases).
3. Compute expected accept or reject without calling the buggy path if possible.
4. Assert exact outcome (status, exception type, membership set, payload field).
5. Cap examples and set deadline=None for CBOR/crypto-heavy cases.

## MeshChatX examples

- Protocol: `tests/backend/test_rrc_protocol_fuzz.py`
- ACL/membership: `tests/backend/test_rrc_oracle_bugs.py`
- Room keys: `tests/backend/test_rrc_room_keys.py`
- EECT shared asserts: `tests/backend/eect/asserts.py`

## Commands

```bash
uv run pytest tests/backend/test_rrc_oracle_bugs.py tests/backend/test_rrc_protocol_fuzz.py -q --tb=short
task test:eect
```

Also read: `.agents/conventions/tests.md`, `.agents/skills/exploratory-testing/SKILL.md`.
