# Contributing to Reticulum MeshChatX

Two paths: **GitHub pull requests** (full dev workflow below) and **LXMF patches** over the mesh (format-patch section).

## Development workflow (GitHub)

1. Fork or clone, then install dependencies:

    ```bash
    task install
    ```

2. Create a branch and make focused changes. Match nearby style and keep SPDX headers on new files.

3. Before you push, run the same gates CI uses:

    ```bash
    task check          # format, lint, test (full gate)
    # or narrower:
    task format
    task lint
    task test:quick
    ```

4. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (feat:, fix:, chore:, etc.). Details: .agents/conventions/commits.md.

5. Open a pull request against master or dev. CI runs task lint, frontend tests, and localization checks.

### Code style

| Surface  | Tool                            | Task                                     |
| -------- | ------------------------------- | ---------------------------------------- |
| Python   | Ruff                            | task format:backend, task lint:backend   |
| Frontend | Prettier, ESLint, vue-tsc, knip | task format:frontend, task lint:frontend |

Editor baseline: .editorconfig. Agent conventions: .agents/conventions/.

### Commit signing

Project commits are signed with rngcs, which binds each commit to a Reticulum identity using Git's SSH signature format. Verification is fully offline: no keyserver, no allowed-signers file, only rngcs installed.

Setup for maintainers and mesh contributors:

```bash
pip install rns                       # rngcs ships inside the rns package
rnid -g ~/.rngit/client_identity      # once, creates your signing identity
rnid -i ~/.rngit/client_identity -p   # prints your 32-char identity hash

git config --local gpg.format ssh
git config --local gpg.ssh.program rngcs
git config --local gpg.ssh.allowedsignersfile none
git config --local user.signingKey ~/.rngit/client_identity
git config --local user.email <your-identity-hash>
git config --local commit.gpgsign true
```

The author email must equal the signing identity hash. Verification fails when the author and signer differ, and the same binding keeps `Signed-off-by:` trailers working for DCO-style checks.

Add a `.mailmap` line so `git log`, `shortlog`, and `blame` stay readable while the raw author field stays identity-bound:

```
Your Name <you@example.com> <your-identity-hash>
```

Verify locally with `git log --show-signature`. `git log --format=%G?` reports `G` for a verified rngcs signature, `E` when rngcs is not installed, and `N` for unsigned commits. GitHub cannot parse the RSG payload, so commits show no verified badge there and hash-authored commits do not link to a GitHub account; that is the accepted trade-off for offline-verifiable, identity-bound signatures over `rns://` remotes.

Unsigned or GPG-signed pull requests from outside contributors are still accepted.

---

## Generating a patch (LXMF)

1. Clone or fork the repository and make your changes on a branch.

2. Stage and commit your work:

    ```bash
    git add -A
    git commit -m "Short description of the change"
    ```

3. Export the commit(s) as a .patch file:

    ```bash
    # Single most recent commit
    git format-patch -1

    # Last N commits
    git format-patch -N

    # All commits since a branch point
    git format-patch main..HEAD
    ```

    This produces one .patch file per commit (for example 0001-my-change.patch).

## Sending the patch

Send the .patch file as an LXMF message over Reticulum to:

```
f489752fbef161c64d65e385a4e9fc74
```

You can attach the file using Sideband, Meshchat, MeshchatX, or any LXMF-capable client with attachments support. Include a brief description of what the patch does in the message body.

Lastly, be patient.

## Patch guidelines (LXMF)

- Keep patches focused on a single change or fix.
- Test your changes before exporting.
- Hooks, lint, and tests are optional for mesh patches but strongly recommended when you have the toolchain.
- GitHub contributors should run task lint and add tests when behaviour changes.

## Licensing of contributions

By submitting a patch, you agree that your contribution is licensed under the same terms as the file or files it modifies, as recorded by the per-file SPDX headers and the repository LICENSE:

- Contributions to project-owned files (SPDX 0BSD) are licensed under 0BSD.
- Contributions to upstream-derived files (SPDX MIT or 0BSD AND MIT) are licensed under MIT, so the upstream license obligations are preserved.
- New files you author and add to the project are licensed under 0BSD unless you explicitly mark them otherwise in the patch.

You also confirm that you have the right to submit the contribution under these terms (for example, it is your own work, or you have permission from the copyright holder), and that you are not knowingly introducing code under an incompatible license.

## Generative AI policy

You may use generative AI tools when contributing, on the condition that your setup actually supplies the model with enough context to produce sound work and your provider does not train on the code, read [Reticulum Zen](https://reticulum.network/manual/zen.html) and the [Reticulum License](https://reticulum.network/manual/license.html). Vague prompts and thin context lead to wrong or generic patches; that burden is on the contributor, not the reviewers.

We strongly prefer models that run locally or offline when that is practical for you or open-weight cloud models by a ZDR (zero data retention) provider.

Contributions must still be yours to justify and maintain. Do not submit bulk-generated changes you have not read, understood, and tested. We are not looking for unreviewed AI output or style-only churn from tools used without engineering/architectural judgment.
