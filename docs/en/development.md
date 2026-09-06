# Development

Contributor workflow: install, format, lint, test, version bumps, and adding locales. Runtime install paths are in **Installation and setup**. Packaging is in **Building from source and packaging**.

## Branches

| Branch | Purpose                                            |
| ------ | -------------------------------------------------- |
| master | Stable releases                                    |
| dev    | Active development. May be incomplete or breaking. |

## Daily commands

```bash
task install
task hooks:install   # pre-commit format/lint + commitlint (once per clone)
task format
task lint
task test
task build
```

Makefile targets call the same Taskfile commands:

| Command      | Delegates to | Description                                                          |
| ------------ | ------------ | -------------------------------------------------------------------- |
| make install | task install | Install pnpm and UV dependencies                                     |
| make run     | task run     | Run MeshChatX via UV                                                 |
| make build   | task build   | Build frontend and backend artifacts                                 |
| make format  | task format  | Format frontend and backend                                          |
| make lint    | task lint    | ESLint, svelte-check, knip, dpdm cycles, Ruff, basedpyright |

`task lint:frontend` also runs `typecheck:features` (strict Svelte/features), full Prettier `format:check`, and circular-dep analysis via dpdm. After `pnpm run build-frontend`, run `task check:frontend-bundle` (or `pnpm run check:bundle-budgets`) to enforce Vite chunk size budgets.
| make test | task test | Frontend and backend tests |
| make clean | task clean | Remove build artifacts and node_modules |
| make tree-rsm-verify | (shell) | Verify meshchatx.rsm signature and hashes |
| make tree-rsm-sign | (shell) | Sign tree inventory (needs RNS_ID_PATH) |
| make hooks-install | task hooks:install | Git hooks: format/lint staged files, commitlint, RSM resign |

For a Vite HMR loop, use task dev as described in **Installation and setup**.

## Lockfiles and install scripts

From a clean clone:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
cd MeshChatX
corepack enable
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "uv==0.11.15"
uv lock --check
uv sync --group dev
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

pnpm install --frozen-lockfile fails if pnpm-lock.yaml does not match package.json, so an unexpected upstream version cannot land silently. Store integrity is also on in pnpm-workspace.yaml. The extra pnpm config set line hardens the user-level config too.

pnpm v11+ blocks lifecycle scripts by default. Only packages listed under allowBuilds in pnpm-workspace.yaml may run install scripts (electron, electron-winstaller, esbuild). uv lock --check fails if uv.lock is out of date with pyproject.toml. uv sync then installs from the lockfile only. Pin UV with pip install "uv==0.11.15" to match CI.

To update dependencies on purpose, run pnpm update or uv lock in its own commit and read the lockfile diff before you push.

## Versioning

Edit the version field in package.json, then run pnpm run version:sync (also the first step of pnpm run build). That copies the number into pyproject.toml, the Python version modules, Android Gradle, electron/app-version.json, the README and translated READMEs, the Raspberry Pi pipx example, Arch PKGBUILD helpers, third-party notices, and GitHub issue-template placeholders.

pnpm run version:sync also runs scripts/bake_build_meta.js, which writes gitignored _build_meta_baked.py with commit, product channel (testing / beta / stable / local), and release/channel_prompt.json. Override channel with MESHCHATX_BUILD_CHANNEL.

Changelog entries are still written by hand when you cut a release. meshchatx.**version** is read from meshchatx/src/version.py without importing meshchatx.src, so import meshchatx stays lightweight.

## Release channels

| Channel | Tags                       | How to cut                                                           |
| ------- | -------------------------- | -------------------------------------------------------------------- |
| Testing | nightly-* (also testing-*) | Daily cron / Testing Release workflow from dev                       |
| Beta    | beta-* (also preview-*)    | Beta Release workflow_dispatch (CI must be green on that SHA)        |
| Stable  | vX.Y.Z                     | Promote Release to Stable, or tag vX.Y.Z on the same SHA Beta tested |
| Local   | (none)                     | Source checkout / unset bake                                         |

Before a Testing or Beta cut, edit release/channel_prompt.json (focus_areas, notes). Bug reports go to bug_report_lxmf in that file (swap later for an issues bot destination). The app shows that copy once per build on Testing/Beta and always on About.

### Release ops checklist

1. Edit release/channel_prompt.json if you want focus areas for testers.
2. Cut Testing (automatic) or Beta (Beta Release / Promote Release).
3. For Stable, promote the **same SHA** that shipped as Beta (rebuild is required so channel bake flips to stable. Do not copy Beta assets onto a Stable release).
4. Review the Stable **draft** GitHub release (assets, SLSA, cosign), then publish. Immutable releases cannot gain assets after publish.
5. Rollback: publish a new Stable from a known-good prior SHA. Do not rewrite a published release.
6. Users see the channel badge in the sidebar and About. Testing/Beta also get a one-time prompt.
7. Flatpak: the tag's `flatpak-ostree` job publishes to `https://cdn.meshchatx.com/flatpak/` on branch `testing`, `beta`, or `stable`. Keep that OSTree tree under `flatpak/` only. After the first good CDN publish, disable GitHub Pages if it still hosts the old Flatpak tree.
8. Bunny pull zone (`cdn.meshchatx.com`): long cache on `/flatpak/repo/objects/*` and `/deltas/*`. No cache or must-revalidate on `summary*`, `refs`, `config`, and `*.flatpakref` / `*.flatpakrepo`.

Hard rule for CI speed: cache toolchains and downloads only. Tagged release binaries must be built inside that tag's single build-release run_id. Never attach artifacts from another run.

Prerelease retention: keep about 7 Testing and 5 Beta GitHub prereleases (scripts/ci/github-prune-channel-prereleases.sh). Stable releases are never auto-deleted.

## Adding a language

Locale discovery is automatic. Add a file under meshchatx/src/frontend/locales/ (for example xx.json) with the same keys as en.json and a top-level _languageName string for the selector label. Copy en.json and translate the values. Machine-assisted generation is optional.

For a machine-generated first draft from en.json, use scripts/argos_translate.py. It keeps interpolation variables such as `{count}` intact.

```bash
pipx install argostranslate
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "Your Language Name"
```

After a machine pass, have an LLM or a human check grammar, context, and tone.

```bash
pnpm test -- tests/frontend/i18n.test.js --run
```

That checks key parity with en.json. No other code changes. The app, language selector, and tests pick up locales from meshchatx/src/frontend/locales/ at build time.

Translation fixes are welcome via LXMF (f489752fbef161c64d65e385a4e9fc74) or a pull request.

In-app MeshChatX guides under docs/en/ are English today. Localized landing pages exist for the Reticulum manual tab.

## See also

- **Architecture and design** for process layout and managers
- **Building from source and packaging** for offline and APK builds
- .agents/ for contributor agent conventions (not shipped in-app)
