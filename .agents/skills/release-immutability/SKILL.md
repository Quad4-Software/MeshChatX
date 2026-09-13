---
name: release-immutability
description: GitHub and rngit release immutability, tag handling, and release workflow. Use when creating, publishing, or repairing releases.
---

# Skill: release-immutability

Do not create GitHub releases manually when the repository has an automated release pipeline. Tags and releases are immutable once published.

## When to use

- Creating or publishing a new release
- Pushing a release tag
- Uploading wheels or release assets
- Deciding whether to delete, edit, or re-run a release

## Do not do

- Do not run `gh release create` for a stable `vX.Y.Z` tag. The `build-release.yml` workflow owns that action.
- Do not create a published GitHub release before the `build-release.yml` workflow has finished uploading assets. A published release cannot accept new assets in this repository.
- Do not delete Git tags after they have been pushed to GitHub or rngit. Tags are immutable public history.
- Do not bypass branch protection, required checks, or merge queues to rush a release.
- Do not delete an rngit release unless a replacement has already been verified and the user explicitly confirms.

## Why

The `build-release.yml` `draft-github-release` job runs `scripts/ci/github-draft-release-upload-assets.sh`. That script:

1. Creates the release as a **draft**.
2. Builds and uploads all assets (Linux packages, Electron builds, Flatpak, Android APKs, SLSA provenance, cosign bundles).
3. For stable tags, it **leaves the release as a draft** for human review and manual publish.
4. For `nightly-`, `testing-`, `beta-`, or `preview-` tags, it auto-publishes as a prerelease.

If a release already exists and is **not a draft**, the script exits with:

```
Release vX.Y.Z is already published.
Immutable releases cannot accept new assets after publish.
```

This means a manually created release blocks the workflow from attaching built assets.

## Correct flow for a stable release

1. Merge the release PR.
2. Tag the merge commit: `git tag -a vX.Y.Z -m "Release X.Y.Z"`.
3. Push the tag: `git push origin vX.Y.Z`.
4. Wait for the `build-release.yml` workflow to:
    - build assets,
    - create a **draft** release,
    - upload all assets.
5. Review the draft release on GitHub.
6. Publish the draft manually when ready.

## rngit releases

Use `scripts/rngit_release.py`. It wraps `python -m RNS.Utilities.rngit.server release` plus the wheel/pyz builds:

```bash
python3 scripts/rngit_release.py release vX.Y.Z --notes-file /path/to/notes.md
```

That builds the wheel and pyz into `python-dist/`, signs and uploads everything, then fetches the manifest back and verifies it. Pass `--changelog` to reuse the changelog section as notes, or `--edit` for an interactive editor. `create` accepts `-L`/`--local` to generate the manifest and signatures without uploading.

Manual equivalents and gotchas:

- The release remote is the same `rns://...` URL used for `git clone` (see README).
- The signing identity is the rngit client identity (`~/.rngit/client_identity`), used by default. Do not pass a different `-i` identity; the server answers "Not allowed" during init if the identity is not the repo publisher.
- Artifacts dir convention is `python-dist/`. Build with `uv build --wheel && python3 scripts/move_wheels.py`, then `PYZ_OUTPUT=python-dist/meshchatx-X.Y.Z.pyz SKIP_WHEEL=1 bash scripts/build-pyz.sh` so the pyz ships with the wheel.
- rngit writes `manifest.rsm` and `*.rsg` into the artifacts dir. Remove them before re-running create or they upload as artifacts. The helper script does this automatically.
- Notes come from $EDITOR (client_config sets nano). `#` comment lines are stripped on save, but text typed without a leading newline merges into the template's first comment line and survives. The helper script avoids this by injecting notes non-interactively.
- `fetch` takes `tag:artifact-name` or `latest:name`; the manifest lands as `<RepoName>_<tag>.rsm` in the cwd.
- `verify` is offline only: `rngit release -o <manifest.rsm> verify` with the artifacts beside the manifest.
- `delete` prompts `y/N` (the script's `--yes` answers it). Recreate right after if the delete was for a notes or artifact fix.
- rngit releases can be created after the GitHub draft is ready. They do not conflict with the GitHub release workflow.
- Do not delete an old rngit release until the new one is confirmed on the repository.

## If something goes wrong

- If a GitHub release was created too early, delete **only the GitHub release** (not the tag) and re-run the `draft-github-release` job. The script will create a new draft against the existing tag.
- If a tag was pushed by mistake, do not delete it. Prepare the next version and use that tag instead.
- If CI is failing, fix the failures. Do not merge, tag, or release while required checks are red.

## Verification

- `gh release view vX.Y.Z --json isDraft,assets` should show `isDraft: true` with all assets attached before manual publish.
- `rngit release ... list` should show the new release with a valid manifest and wheel.

## Related skills

- `workspace`
- `rngit`
- `ci-security`
