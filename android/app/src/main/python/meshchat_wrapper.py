# SPDX-License-Identifier: 0BSD

import os
import signal
import sys
import threading

# Prevents a second meshchat main() if Java starts two threads (e.g. activity edge cases).
_server_loop_lock = threading.Lock()
_server_loop_active = False


def _ensure_android_reticulum_config(reticulum_config_dir):
    if not reticulum_config_dir:
        return

    config_path = os.path.join(reticulum_config_dir, "config")
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as existing_file:
            content = existing_file.read()
        changed = False
        if "share_instance = Yes" in content:
            content = content.replace("share_instance = Yes", "share_instance = No")
            changed = True
        if "panic_on_interface_error" not in content:
            if "[reticulum]" in content:
                content = content.replace(
                    "[reticulum]",
                    "[reticulum]\n  panic_on_interface_error = No",
                    1,
                )
            else:
                content = "[reticulum]\n  panic_on_interface_error = No\n\n" + content
            changed = True
        if changed:
            with open(config_path, "w", encoding="utf-8") as config_file:
                config_file.write(content)
        return

    with open(config_path, "w", encoding="utf-8") as config_file:
        config_file.write(
            "[reticulum]\n"
            "  share_instance = No\n"
            "  panic_on_interface_error = No\n"
            "\n"
            "[interfaces]\n",
        )


def _patch_asyncio_signal_handlers_for_android():
    try:
        from asyncio import unix_events
    except Exception:
        return None

    loop_cls = getattr(unix_events, "_UnixSelectorEventLoop", None)
    if loop_cls is None:
        return None

    original_add_signal_handler = loop_cls.add_signal_handler

    def _safe_add_signal_handler(self, sig, callback, *args):
        try:
            return original_add_signal_handler(self, sig, callback, *args)
        except (RuntimeError, ValueError) as exc:
            message = str(exc)
            if "set_wakeup_fd only works in main thread" in message:
                return None
            if "main thread of the main interpreter" in message:
                return None
            raise

    loop_cls.add_signal_handler = _safe_add_signal_handler
    return loop_cls, original_add_signal_handler


def _patch_aiohttp_run_app_for_android():
    try:
        from aiohttp import web
    except Exception:
        return None

    original_run_app = web.run_app

    def _safe_run_app(*args, **kwargs):
        kwargs.setdefault("handle_signals", False)
        return original_run_app(*args, **kwargs)

    web.run_app = _safe_run_app
    return web, original_run_app


def _clear_stale_storage_lock(storage_dir):
    """Drop a leftover soft lock from a previous process death.

    Android often lacks flock (ENOSYS), so StorageLock falls back to a PID
    file. After force-stop / crash the old PID may still look "alive" under
    Android's process model, which would make boot exit with SystemExit(1).
    The Java wrapper already serializes start_server, so clearing is safe.
    """
    if not storage_dir:
        return
    lock_path = os.path.join(storage_dir, ".meshchatx.lock")
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except OSError as exc:
        print(f"meshchat_wrapper: could not clear storage lock: {exc}")


def _patch_rns_panic_for_android():
    """Stop RNS.panic/os._exit from killing the whole Android process."""
    try:
        from meshchatx.src.backend.rns_startup_recovery import (
            install_rns_panic_containment,
        )

        return install_rns_panic_containment()
    except Exception as exc:
        print(f"meshchat_wrapper: RNS panic containment skipped: {exc}")
        return False


def _install_android_rnode_support(activity=None):
    try:
        from meshchatx.src.backend.android_rnode import install_android_rnode_support

        ok = install_android_rnode_support(activity)
        if ok:
            print("meshchat_wrapper: Android RNode USB/Bluetooth support ready")
        else:
            print("meshchat_wrapper: Android RNode support not fully configured")
    except Exception as exc:
        print(f"meshchat_wrapper: Android RNode support skipped: {exc}")


def start_server(port=8000, app_files_dir=None, activity=None):
    global _server_loop_active
    with _server_loop_lock:
        if _server_loop_active:
            print("meshchat_wrapper: start_server ignored (server loop already active)")
            return
        _server_loop_active = True
    try:
        storage_dir = None
        reticulum_config_dir = None
        if app_files_dir:
            base_dir = os.path.join(app_files_dir, "meshchatx")
            storage_dir = os.path.join(base_dir, "storage")
            reticulum_config_dir = os.path.join(base_dir, "reticulum")
            os.makedirs(storage_dir, exist_ok=True)
            os.makedirs(reticulum_config_dir, exist_ok=True)
            _ensure_android_reticulum_config(reticulum_config_dir)
            _clear_stale_storage_lock(storage_dir)

        original_signal = signal.signal

        def _safe_signal(sig, handler):
            try:
                return original_signal(sig, handler)
            except ValueError as exc:
                if "main thread of the main interpreter" in str(exc):
                    return None
                raise

        signal.signal = _safe_signal
        asyncio_signal_patch = _patch_asyncio_signal_handlers_for_android()
        aiohttp_run_app_patch = _patch_aiohttp_run_app_for_android()
        _patch_rns_panic_for_android()
        _install_android_rnode_support(activity)
        try:
            from meshchatx.android_codec2 import (
                ensure_codec2_native_library,
                probe_pycodec2,
            )

            ensure_codec2_native_library()
            ok, err = probe_pycodec2()
            if ok:
                print("meshchat_wrapper: Codec2/pycodec2 ready")
            else:
                print(f"meshchat_wrapper: Codec2/pycodec2 unavailable: {err}")
        except Exception as codec2_exc:
            print(f"meshchat_wrapper: Codec2 preload skipped: {codec2_exc}")
        from meshchatx.meshchat import ReticulumMeshChat, main

        try:
            from meshchatx.android_push_bridge import install_websocket_hook

            install_websocket_hook(ReticulumMeshChat)
        except Exception as hook_exc:
            print(f"meshchat_wrapper: install_websocket_hook skipped: {hook_exc}")

        sys.argv = [
            "meshchat",
            "--headless",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
        if storage_dir:
            sys.argv.extend(["--storage-dir", storage_dir])
        if reticulum_config_dir:
            sys.argv.extend(["--reticulum-config-dir", reticulum_config_dir])

        try:
            main()
        finally:
            signal.signal = original_signal
            if asyncio_signal_patch is not None:
                loop_cls, original_add_signal_handler = asyncio_signal_patch
                loop_cls.add_signal_handler = original_add_signal_handler
            if aiohttp_run_app_patch is not None:
                web_module, original_run_app = aiohttp_run_app_patch
                web_module.run_app = original_run_app
    except SystemExit as e:
        # Chaquopy surfaces SystemExit as PyException; re-raise as RuntimeError
        # so Java retry/error UI gets a readable message.
        code = getattr(e, "code", e)
        cause = e.__cause__ or e.__context__
        cause_text = str(cause).strip() if cause is not None else ""
        if cause_text:
            message = f"MeshChatX exited during startup (code={code}): {cause_text}"
        else:
            message = f"MeshChatX exited during startup (code={code})"
        print(f"Error starting MeshChatX server: {message}")
        raise RuntimeError(message) from e
    except Exception as e:
        print(f"Error starting MeshChatX server: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        with _server_loop_lock:
            _server_loop_active = False
