# SPDX-License-Identifier: 0BSD

import os
import signal
import sys


def _ensure_android_reticulum_config(reticulum_config_dir):
    if not reticulum_config_dir:
        return

    config_path = os.path.join(reticulum_config_dir, "config")
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as existing_file:
            content = existing_file.read()
        if "share_instance = Yes" in content:
            content = content.replace("share_instance = Yes", "share_instance = No")
            with open(config_path, "w", encoding="utf-8") as config_file:
                config_file.write(content)
        return

    with open(config_path, "w", encoding="utf-8") as config_file:
        config_file.write("[reticulum]\n  share_instance = No\n\n[interfaces]\n")


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


def start_server(port=8000, app_files_dir=None):
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
        from meshchatx.meshchat import main

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
    except Exception as e:
        print(f"Error starting MeshChatX server: {e}")
        import traceback

        traceback.print_exc()
        raise
