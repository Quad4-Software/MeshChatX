# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: run_self_test."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


def run_self_test(app: Any) -> dict:
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v

    stack_ok = True
    stack_reason = ""
    if not hasattr(app, "reticulum") or app.reticulum is None:
        stack_ok = False
        stack_reason = "Reticulum stack is not initialized"
    else:
        try:
            _ = app.reticulum.config
        except Exception as e:
            stack_ok = False
            stack_reason = f"Reticulum stack internal error: {e!s}"

    config_ok = True
    config_reason = ""
    try:
        if app.config is None:
            config_ok = False
            config_reason = "App configuration is not initialized"
        else:
            _ = app.config.display_name.get()
    except Exception as e:
        config_ok = False
        config_reason = f"App config error: {e!s}"

    if config_ok:
        try:
            reticulum_config_path = app._api_reticulum_config_path()
            if not reticulum_config_path or not os.path.exists(
                reticulum_config_path,
            ):
                config_ok = False
                config_reason = "Reticulum config file not found"
            elif not reticulum_config_has_required_sections(
                reticulum_config_path,
            ):
                config_ok = False
                config_reason = "Reticulum config is missing required sections"
        except Exception as e:
            config_ok = False
            config_reason = f"Reticulum config check failed: {e!s}"

    db_ok = True
    db_reason = ""
    if not app.database:
        db_ok = False
        db_reason = "Database is not initialized"
    else:
        try:
            app.database.execute_sql("SELECT 1").fetchone()
            snapshot = app.database.get_database_health_snapshot()
            if snapshot.get("quick_check") not in ("ok", "unknown"):
                db_ok = False
                db_reason = (
                    f"Database quick check returned: {snapshot.get('quick_check')}"
                )
        except Exception as e:
            db_ok = False
            db_reason = f"Database check failed: {e!s}"

    rw_ok = True
    rw_reason = ""
    try:
        if not app.storage_path or not os.path.exists(app.storage_path):
            rw_ok = False
            rw_reason = "Storage directory does not exist"
        else:
            temp_file_path = os.path.join(app.storage_path, ".self_test_temp")
            test_data = "meshchatx_self_test_write_read_verify"
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(test_data)

            with open(temp_file_path, encoding="utf-8") as f:
                read_data = f.read()

            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            if read_data != test_data:
                rw_ok = False
                rw_reason = "Read data did not match written data"
    except Exception as e:
        rw_ok = False
        rw_reason = f"Read/write test failed: {e!s}"

    from meshchatx.src.backend import self_check as self_check_mod

    bots_ok, bots_reason = app._check_bot_lifecycle()
    identity_result = self_check_mod.check_identity(app.identity)
    imports_result = self_check_mod.check_critical_imports()
    # Fold Python runtime into imports so the UI stays one row.
    runtime_result = self_check_mod.check_python_runtime()
    if runtime_result["status"] != "ok" and imports_result["status"] == "ok":
        imports_result = runtime_result
    elif runtime_result["status"] != "ok":
        imports_result = {
            "status": "failed",
            "reason": f"{imports_result.get('reason') or ''} | {runtime_result.get('reason') or ''}".strip(
                " |",
            ),
        }
    storage_lock_result = self_check_mod.check_storage_lock(
        app.storage_path or app.storage_dir,
    )
    temp_fs_result = self_check_mod.check_temp_filesystem()
    fs_sandbox_result = self_check_mod.check_fs_sandbox()
    public_assets_result = self_check_mod.check_public_assets(app.get_public_path)
    lxmf_result = self_check_mod.check_lxmf_router(
        app.message_router,
        app.local_lxmf_destination,
    )
    subprocess_result = self_check_mod.check_subprocess_spawn()
    run_module_result = self_check_mod.check_meshchatx_run_module()
    storage_base = app.storage_path or app.storage_dir
    sqlite_result = self_check_mod.check_sqlite_roundtrip(storage_base)
    identity_file_result = self_check_mod.check_identity_file_roundtrip(
        storage_base,
    )
    loopback_result = self_check_mod.check_loopback_tcp()
    unicode_result = self_check_mod.check_unicode_path(storage_base)
    rnode_result = self_check_mod.check_rnode_support()
    bot_launcher_result = self_check_mod.check_bot_launcher()
    plugins_runtime_result = self_check_mod.check_plugins_runtime(app)
    web_results = self_check_mod.check_web_stack(app)

    return {
        "stack_up": {
            "status": "ok" if stack_ok else "failed",
            "reason": stack_reason,
        },
        "config_good": {
            "status": "ok" if config_ok else "failed",
            "reason": config_reason,
        },
        "db_good": {
            "status": "ok" if db_ok else "failed",
            "reason": db_reason,
        },
        "read_write_good": {
            "status": "ok" if rw_ok else "failed",
            "reason": rw_reason,
        },
        "identity_good": identity_result,
        "imports_good": imports_result,
        "storage_lock_good": storage_lock_result,
        "temp_fs_good": temp_fs_result,
        "fs_sandbox_good": fs_sandbox_result,
        "public_assets_good": public_assets_result,
        "lxmf_router_good": lxmf_result,
        "subprocess_good": subprocess_result,
        "run_module_good": run_module_result,
        "sqlite_roundtrip": sqlite_result,
        "identity_roundtrip": identity_file_result,
        "loopback_tcp": loopback_result,
        "unicode_path_good": unicode_result,
        "rnode_support_good": rnode_result,
        "bot_launcher_good": bot_launcher_result,
        "http_status_good": web_results.get(
            "http_status_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_app_info_good": web_results.get(
            "http_app_info_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_config_good": web_results.get(
            "http_config_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_db_health_good": web_results.get(
            "http_db_health_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_auth_csrf_good": web_results.get(
            "http_auth_csrf_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_bots_status_good": web_results.get(
            "http_bots_status_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_security_good": web_results.get(
            "http_security_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_interfaces_good": web_results.get(
            "http_interfaces_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_reticulum_instance_good": web_results.get(
            "http_reticulum_instance_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_identities_good": web_results.get(
            "http_identities_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_favourites_good": web_results.get(
            "http_favourites_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_telephone_good": web_results.get(
            "http_telephone_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_plugins_good": web_results.get(
            "http_plugins_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_plugins_trust_good": web_results.get(
            "http_plugins_trust_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_sideband_plugins_good": web_results.get(
            "http_sideband_plugins_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_sideband_config_good": web_results.get(
            "http_sideband_config_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_rrc_hubs_good": web_results.get(
            "http_rrc_hubs_good",
            {"status": "failed", "reason": "missing"},
        ),
        "http_rrc_servers_good": web_results.get(
            "http_rrc_servers_good",
            {"status": "failed", "reason": "missing"},
        ),
        "plugins_runtime_good": plugins_runtime_result,
        "websocket_good": web_results.get(
            "websocket_good",
            {"status": "failed", "reason": "missing"},
        ),
        "websocket_rns_link_good": web_results.get(
            "websocket_rns_link_good",
            {"status": "failed", "reason": "missing"},
        ),
        "bots_lifecycle": {
            "status": "ok" if bots_ok else "failed",
            "reason": bots_reason,
        },
    }
