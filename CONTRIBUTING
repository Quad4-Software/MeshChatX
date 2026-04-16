# Contributing to Reticulum MeshChatX

Patches are the preferred way to contribute. Create your changes locally, export a `.patch` file, and send it over Reticulum.

## Generating a patch

1. Clone or fork the repository and make your changes on a branch.

2. Stage and commit your work:

   ```bash
   git add -A
   git commit -m "Short description of the change"
   ```

3. Export the commit(s) as a `.patch` file:

   ```bash
   # Single most recent commit
   git format-patch -1

   # Last N commits
   git format-patch -N

   # All commits since a branch point
   git format-patch main..HEAD
   ```

   This produces one `.patch` file per commit (for example `0001-my-change.patch`).

## Sending the patch

Send the `.patch` file as an LXMF message over Reticulum to:

```
7cc8d66b4f6a0e0e49d34af7f6077b5a
```

You can attach the file using Sideband, Meshchat, MeshchatX, or any LXMF-capable client with attachments support. Include a brief description of what the patch does in the message body.

Lastly, be patient.

## Patch guidelines

- Keep patches focused on a single change or fix.
- Test your changes before exporting.
- No need to run linting or formatting.
- No need to add a test or run the test suite.

## Licensing of contributions

By submitting a patch, you agree that your contribution is licensed under the same terms as the file or files it modifies, as recorded by the per-file SPDX headers and the repository `LICENSE`:

- Contributions to project-owned files (SPDX `0BSD`) are licensed under 0BSD.
- Contributions to upstream-derived files (SPDX `MIT` or `0BSD AND MIT`) are licensed under MIT, so the upstream license obligations are preserved.
- New files you author and add to the project are licensed under 0BSD unless you explicitly mark them otherwise in the patch.

You also confirm that you have the right to submit the contribution under these terms (for example, it is your own work, or you have permission from the copyright holder), and that you are not knowingly introducing code under an incompatible license.

## Generative AI policy

You may use generative AI tools when contributing, on the condition that your setup actually supplies the model with enough context to produce sound work: relevant files, constraints, failing tests, and project conventions. Vague prompts and thin context lead to wrong or generic patches; that burden is on the contributor, not the reviewers.

You must disclose AI usage in the patch message body (or commit message, if you prefer): state which tools or services you used in a material way for that change (for example, model or product name, and whether it was local or cloud). If a change was written without meaningful AI assistance, say so briefly. This is so reviewers can judge scope and provenance; it is not a substitute for your own review and testing.

We prefer models that run locally or offline when that is practical for you.

Contributions must still be yours to justify and maintain. Do not submit bulk-generated changes you have not read, understood, and tested. We are not looking for unreviewed AI output or style-only churn from tools used without engineering/architectural judgment.