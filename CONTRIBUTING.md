# Contributing to Reticulum MeshChatX

Two paths: **GitHub pull requests** (full dev workflow below) and **LXMF patches** over the mesh (format-patch section).

## Development workflow (GitHub)

1. Fork or clone, then install dependencies:

    ```bash
    task install
    task hooks:install
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

4. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (feat:, fix:, chore:, etc.). Details: .agents/conventions/commits.md. With hooks installed, commitlint runs on every commit.

5. Open a pull request against master or dev. CI runs task lint, frontend tests, and localization checks.

### Git hooks

task hooks:install enables tracked hooks under .githooks/:

| Hook       | What it does                                                                                             |
| ---------- | -------------------------------------------------------------------------------------------------------- |
| pre-commit | Ruff format/lint, Prettier, ESLint fix on staged files, whitespace checks, optional meshchatx.rsm resign |
| commit-msg | commitlint (conventional commit header)                                                                  |

Skip one hook:

```bash
SKIP=ruff-format git commit ...
```

Skip all hooks:

```bash
git commit --no-verify
```

Skip RSM resign only:

```bash
SKIP=meshchatx-rsm git commit ...
```

### Code style

| Surface  | Tool                            | Task                                     |
| -------- | ------------------------------- | ---------------------------------------- |
| Python   | Ruff                            | task format:backend, task lint:backend   |
| Frontend | Prettier, ESLint, vue-tsc, knip | task format:frontend, task lint:frontend |

Editor baseline: .editorconfig. Agent conventions: .agents/conventions/.

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

You must disclose AI usage in the patch message body (or commit message, if you prefer): state which tools or services you used in a material way for that change (for example, model or product name, and whether it was local or cloud). If a change was written without meaningful AI assistance, say so briefly. This is so reviewers can judge scope and provenance; it is not a substitute for your own review and testing.

We strongly prefer models that run locally or offline when that is practical for you.

Contributions must still be yours to justify and maintain. Do not submit bulk-generated changes you have not read, understood, and tested. We are not looking for unreviewed AI output or style-only churn from tools used without engineering/architectural judgment.
