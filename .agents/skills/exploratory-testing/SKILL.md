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

## Patch safety (AI repair caveats)

APR research findings that shape how fixes land:

- LLMs claim bugs in correct code, and repair of buggy code damages correct code
  more often than it helps. No oracle, no edit. A hypothesis without a failing
  test stays a report item, not a patch.
- Multi-turn fixes accumulate regressions: 40 to 73 percent of tasks lose
  earlier-correct behaviour across a session. After every patch, re-run the
  prior oracle tests and the suites of direct consumers, not only the new test.
- Regression rate grows with churn. Keep patches minimal and local. No
  refactors, renames, or drive-by cleanups inside a bugfix.
- Test overfitting: a patch can pass the new test and still violate the
  invariant. Assert the invariant, not only the trigger input. Add at least one
  neighbouring input that must behave the same way.
- Hallucinated localisation: a patch can silence the symptom while the real
  cause is upstream. State the bug mechanism in one sentence before editing.
  If the patch does not address that mechanism, stop and re-trace.
- Iterative repair reintroduces security regressions. After a fix, re-check the
  security invariants listed below even when the fix is not security code.

## Cascade checklist after any fix

- Grep every caller and importer of the changed symbol; skim each use site.
- Run the focused suite plus the suites of direct consumers.
- If the file sits in a scanned tree, run the contract scanners:
  HTTP routes, WS manifest, schema versions, frontend ownership.
- Check symmetric paths: encode/decode, lock/unlock, add/remove,
  connect/disconnect, enable/disable.
- Security invariants unchanged: CSRF on mutating HTTP, WS mutator denylist,
  path jail, URL origin allowlists, Landlock roots, privacy-mode egress block,
  plugin permission gates.
- Record intentional behaviour that looks buggy but is deliberate, so a later
  hunt does not fix it.

## Multi-agent hunts

- Charter subagents by domain (concurrency, path jail, wire protocol), not by
  directory listing. Give each the module-ownership row it covers.
- Subagents return hypotheses with file:line, evidence, and predicted wrong
  behaviour. They do not patch.
- Dedupe overlapping hypotheses before confirming; the same root cause often
  surfaces in two charters.
- Confirm and fix serially per file. Parallel fixers on shared files corrupt
  each others context and produce half-applied patches.

## Deliverable shape

When reporting to the user:

- Confirmed bugs (fixed or still open)
- Oracle tests added
- Intentional behaviours left alone
- Remaining hypotheses not yet tested
- Rejected hypotheses (looked buggy, verified correct) worth recording

## Related

- `.agents/skills/test-oracles/SKILL.md`
- `.agents/skills/rrc-relay-chat/SKILL.md`
- `.agents/skills/reticulum-design-gates/SKILL.md`
- `.agents/skills/url-origin-allowlists/SKILL.md`
- `.agents/conventions/tests.md`
