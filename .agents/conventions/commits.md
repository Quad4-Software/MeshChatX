# Commit message conventions

MeshChatX uses [Conventional Commits](https://www.conventionalcommits.org/) for git history on GitHub. LXMF patch contributors can use any short message in their local commit before git format-patch.

## Format

```
<type>: <subject>

[optional body]

[optional footer]
```

- **type**: one of feat, fix, refactor, chore, docs, test, ci, build, perf, style, revert
- **subject**: imperative, lowercase after the colon, no trailing period, max 120 characters for the full header
- **body**: wrap at 72 characters when you need context. Mention AI tooling here if required by CONTRIBUTING.md

## Examples

```
feat: add path request metrics to RN status page
```

```
fix: close SQLite connections on identity switch teardown
```

```
chore: bump version to 4.8.6 and refresh lockfiles
```

## Signing

This repo's local git config signs with rngcs (Reticulum identity, SSH signature format), not GPG. The author email is the signing identity hash and `.mailmap` maps it to the canonical name. Do not switch the config back to GPG and do not rewrite `user.email`. `%G?` reports `G` for verified rngcs signatures, `E` when rngcs is missing, `N` for unsigned. Setup details: `CONTRIBUTING.md` section "Commit signing".

## Validation

- **manual**: task check:commits or ./node_modules/.bin/commitlint --from origin/master --to HEAD
- **CI**: task check:commits on pull requests

## Related commands

| Command     | Purpose                                           |
| ----------- | ------------------------------------------------- |
| task format | Format the full tree (Prettier, ESLint fix, Ruff) |
| task lint   | Full lint gate (same as CI lint job)              |
| task check  | format, lint, and test before push                |

Config: commitlint.config.cjs.
