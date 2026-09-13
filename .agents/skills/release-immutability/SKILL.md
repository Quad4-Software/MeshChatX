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

- Build the wheel locally: `uv build --wheel`.
- Verify and sign the manifest: `rngit release ... create vX.Y.Z:python-dist/`.
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
