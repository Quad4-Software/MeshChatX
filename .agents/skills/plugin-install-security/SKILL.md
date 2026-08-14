---
name: plugin-install-security
description: Plugin install, RSG signatures, permissions, WASM/Python/Sideband runtimes. Use when changing install/enable/invoke or adding KNOWN_HOOKS / KNOWN_MANAGERS.
---

# Skill: plugin-install-security

Install, sign, permission-grant, and sandbox plugins without bypassing RSG, integrity, or runtime guards.

## When to use

- Adding or changing plugin install / enable / invoke flows
- Declaring new hooks or manager capabilities
- Touching WASM, Python, or Sideband plugin runtimes
- Debugging "permission denied", signature failures, or silent disable after tamper

## Threat model (short)

Plugins are powerful. Treat install and enable as security-sensitive.

| Runtime                   | Risk   | Notes                                     |
| ------------------------- | ------ | ----------------------------------------- |
| Frontend Worker           | Medium | Capability grants, isolated storage modes |
| Backend WASM              | Medium | wasmtime fuel / capability gates          |
| Backend Python / Sideband | High   | Explicit danger / permission gating       |

## Required flow

1. Preview install (permissions, endpoints, signature status)
2. User consent on declared permissions / network endpoints
3. Enable only after grants are stored
4. Runtime enforces declared + granted hooks / managers / storage / `network:fetch`
5. Integrity hashing after install. Tampered trees disable, they do not silently run. `invoke` and `dispatch_hook` re-hash before backend execution.
6. Python backends purge `__pycache__` next to the entry file on load so excluded bytecode cannot replace hashed source.

## Hard rules

- Invalid RSG signatures **hard-block** install. Do not add bypass paths.
- ZIP extract must use zip-slip safe extraction. WASM must pass `validate_wasm_file`.
- New hooks go in `KNOWN_HOOKS`. New managers go in `KNOWN_MANAGERS` in `plugin_permissions.py`.
- Network endpoint scanning parses the URL host. A remote URL is not local because the string contains `127.0.0.1` or `localhost`.
- Plugin i18n lives in the plugin bundle (`locales/{locale}.json`), not core `en.json`.
- Disable everything with `--disable-plugins` / `MESHCHAT_DISABLE_PLUGINS=true` when diagnosing.

## Key files

- `meshchatx/src/backend/plugin_manager.py`
- `meshchatx/src/backend/plugin_guard.py`
- `meshchatx/src/backend/plugin_permissions.py`
- `meshchatx/src/backend/plugin_signature.py`
- `meshchatx/src/backend/plugin_integrity.py`
- `meshchatx/src/backend/plugin_python_runtime.py`
- `meshchatx/src/frontend/js/plugins/pluginWorker.js`
- `meshchatx/src/backend/data/plugins/mcx-bugs/` (reference plugin)

## Verification

```bash
uv run pytest tests/backend/test_plugin_manager.py tests/backend/test_plugin_permissions.py tests/backend/test_plugin_signature.py tests/backend/test_plugin_integrity.py tests/backend/test_plugin_python_runtime.py tests/backend/test_plugin_security.py -q --tb=short
```

Add focused coverage when changing grant normalization, network endpoint scanning, or invoke paths.
