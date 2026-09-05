# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info info."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.app_info._names import *  # noqa: F403, F405


def register_app_info_info_routes(routes, app):

    @routes.get("/api/v1/app/sessions")
    async def app_sessions(_request):
        return web.json_response(app.get_active_sessions_payload())

    # get app info

    # get app info
    @routes.get("/api/v1/app/info")
    async def app_info(request):
        process = getattr(app, "_host_process", None)
        if process is None:
            try:
                process = psutil.Process()
            except Exception:
                process = None

        def _safe_memory_info():
            if process is None:

                class _EmptyMem:
                    rss = 0
                    vms = 0

                return _EmptyMem()
            try:
                return process.memory_info()
            except Exception:

                class _EmptyMemFallback:
                    rss = 0
                    vms = 0

                return _EmptyMemFallback()

        def _safe_process_usage():
            usage: dict[str, float | int | None] = {
                "cpu_percent": None,
                "num_threads": None,
                "num_fds": None,
                "nofile_soft": None,
                "nofile_hard": None,
                "create_time": None,
                "cpu_time_seconds": None,
            }
            if process is None:
                return usage
            try:
                usage["cpu_percent"] = float(process.cpu_percent(interval=None))
            except Exception:
                pass
            try:
                usage["num_threads"] = int(process.num_threads())
            except Exception:
                pass
            try:
                usage["num_fds"] = int(process.num_fds())
            except Exception:
                pass
            try:
                import resource

                soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                usage["nofile_soft"] = int(soft)
                usage["nofile_hard"] = int(hard)
            except Exception:
                pass
            try:
                usage["create_time"] = float(process.create_time())
            except Exception:
                pass
            try:
                times = process.cpu_times()
                usage["cpu_time_seconds"] = float(times.user) + float(times.system)
            except Exception:
                pass
            return usage

        def _safe_battery_usage():
            tracker = getattr(app, "battery_usage", None)
            if tracker is None:
                return None
            try:
                return tracker.snapshot(process)
            except Exception:
                return None

        def _safe_resource_breakdown():
            try:
                from meshchatx.src.backend.process_resource_breakdown import (
                    build_resource_breakdown,
                )

                return build_resource_breakdown(process)
            except Exception:
                return []

        def _safe_net_io():
            try:
                return psutil.net_io_counters()
            except Exception:

                class _N:
                    bytes_sent = 0
                    bytes_recv = 0
                    packets_sent = 0
                    packets_recv = 0

                return _N()

        # psutil often raises on Android (restricted /proc), so never fail the whole payload.
        memory_info = _safe_memory_info()
        process_usage = _safe_process_usage()
        battery_usage = _safe_battery_usage()
        resource_breakdown = _safe_resource_breakdown()
        net_io = _safe_net_io()

        def _safe_database_path():
            if app.database_path:
                return app.database_path
            try:
                if app.database is not None and app.database.provider is not None:
                    return app.database.provider.db_path
            except Exception:
                pass
            return None

        def _safe_sqlite_pragma(name, default=None):
            try:
                if app.database is not None:
                    return app.database._get_pragma_value(name, default)
            except Exception:
                pass
            return default

        def _safe_config_get(name, default):
            try:
                if app.config is not None:
                    return app.config.get(name, default)
            except Exception:
                pass
            return default

        def _safe_user_guidance():
            try:
                guidance = app.build_user_guidance_messages()
                if isinstance(guidance, list):
                    return guidance
            except Exception:
                pass
            return []

        # Get total paths
        total_paths = 0
        is_connected_to_shared_instance = False
        shared_instance_address = None
        if hasattr(app, "reticulum") and app.reticulum:
            try:
                path_table = app.reticulum.get_path_table()
                total_paths = len(path_table)
            except Exception:
                pass

            is_connected_to_shared_instance = getattr(
                app.reticulum,
                "is_connected_to_shared_instance",
                False,
            )

            if is_connected_to_shared_instance:
                # Try to find the shared instance address from active connections
                try:
                    if process is not None:
                        for conn in process.net_connections(kind="all"):
                            if conn.status == psutil.CONN_ESTABLISHED and conn.raddr:
                                # Check for common Reticulum shared instance ports or UNIX sockets
                                if (
                                    isinstance(conn.raddr, tuple)
                                    and conn.raddr[1] == 37428
                                ):
                                    shared_instance_address = (
                                        f"{conn.raddr[0]}:{conn.raddr[1]}"
                                    )
                                    break
                                if (
                                    isinstance(conn.raddr, str)
                                    and (
                                        "rns" in conn.raddr or "reticulum" in conn.raddr
                                    )
                                    and ".sock" in conn.raddr
                                ):
                                    shared_instance_address = conn.raddr
                                    break
                except Exception:
                    pass

                # Fallback to reading config if not found via connections
                if not shared_instance_address:
                    try:
                        config_dir = app._normalize_reticulum_config_dir(
                            getattr(app, "reticulum_config_dir", None),
                        )

                        config_path = os.path.join(config_dir, "config")
                        if os.path.isfile(config_path):
                            cp = configparser.ConfigParser()
                            try:
                                cp.read(config_path)
                            except configparser.Error:
                                pass
                            if cp.has_section("reticulum"):
                                shared_port = cp.getint(
                                    "reticulum",
                                    "shared_instance_port",
                                    fallback=37428,
                                )
                                shared_bind = cp.get(
                                    "reticulum",
                                    "shared_instance_bind",
                                    fallback="127.0.0.1",
                                )
                                shared_instance_address = f"{shared_bind}:{shared_port}"
                    except Exception:
                        pass

        # Calculate announce rates
        current_time = time.time()
        announces_per_second = len(
            [t for t in app.announce_timestamps if current_time - t <= 1.0],
        )
        announces_per_minute = len(
            [t for t in app.announce_timestamps if current_time - t <= 60.0],
        )
        announces_per_hour = len(
            [t for t in app.announce_timestamps if current_time - t <= 3600.0],
        )

        # Clean up old announce timestamps (older than 1 hour)
        app.announce_timestamps = [
            t for t in app.announce_timestamps if current_time - t <= 3600.0
        ]

        # Calculate average download speed
        avg_download_speed_bps = None
        if app.download_speeds:
            total_bytes = sum(size for size, _ in app.download_speeds)
            total_duration = sum(duration for _, duration in app.download_speeds)
            if total_duration > 0:
                avg_download_speed_bps = total_bytes / total_duration

        try:
            db_files = (
                app.database._get_database_file_stats()
                if app.database is not None
                else {
                    "main_bytes": 0,
                    "wal_bytes": 0,
                    "shm_bytes": 0,
                    "total_bytes": 0,
                }
            )
        except Exception:
            db_files = {
                "main_bytes": 0,
                "wal_bytes": 0,
                "shm_bytes": 0,
                "total_bytes": 0,
            }

        return web.json_response(
            {
                "app_info": {
                    "version": app.get_app_version(),
                    **(app.get_build_meta() if hasattr(app, "get_build_meta") else {}),
                    "lxmf_version": LXMF.__version__,
                    "rns_version": RNS.__version__,
                    "lxst_version": app.get_lxst_version(),
                    "python_version": platform.python_version(),
                    "dependencies": {
                        "aiohttp": app.get_package_version("aiohttp"),
                        "aiohttp_session": app.get_package_version(
                            "aiohttp-session",
                        ),
                        "cryptography": app.get_package_version("cryptography"),
                        "psutil": app.get_package_version("psutil"),
                        "websockets": app.get_package_version("websockets"),
                        "audioop_lts": (
                            app.get_package_version("audioop-lts")
                            if sys.version_info >= (3, 13)
                            else "n/a"
                        ),
                        "ply": app.get_package_version("ply"),
                        "bcrypt": app.get_package_version("bcrypt"),
                        "lxmfy": app.get_package_version("lxmfy"),
                        "rns_filesync": app.get_package_version("rns-filesync"),
                    },
                    "storage_path": app.storage_path,
                    "database_path": _safe_database_path(),
                    "database_file_size": db_files["main_bytes"],
                    "database_files": db_files,
                    "sqlite": {
                        "journal_mode": _safe_sqlite_pragma(
                            "journal_mode",
                            "unknown",
                        ),
                        "synchronous": _safe_sqlite_pragma("synchronous", None),
                        "wal_autocheckpoint": _safe_sqlite_pragma(
                            "wal_autocheckpoint",
                            None,
                        ),
                        "busy_timeout": _safe_sqlite_pragma("busy_timeout", None),
                        "temp_store": _safe_sqlite_pragma("temp_store", None),
                        "cache_size": _safe_sqlite_pragma("cache_size", None),
                        "mmap_size": _safe_sqlite_pragma("mmap_size", None),
                        "memory_relaxed": bool(
                            getattr(
                                app.database,
                                "_sqlite_memory_relaxed",
                                False,
                            )
                            if app.database is not None
                            else False,
                        ),
                    },
                    "reticulum_config_path": app._api_reticulum_config_path(),
                    "host_platform": sys.platform,
                    **app._landlock_status_dict(),
                    "is_connected_to_shared_instance": is_connected_to_shared_instance,
                    "shared_instance_address": shared_instance_address,
                    "is_transport_enabled": (
                        app.reticulum.transport_enabled()
                        if hasattr(app, "reticulum") and app.reticulum
                        else False
                    ),
                    "memory_usage": {
                        "rss": memory_info.rss,
                        "vms": memory_info.vms,
                        "cpu_percent": process_usage.get("cpu_percent"),
                        "num_threads": process_usage.get("num_threads"),
                        "num_fds": process_usage.get("num_fds"),
                        "nofile_soft": process_usage.get("nofile_soft"),
                        "nofile_hard": process_usage.get("nofile_hard"),
                        "create_time": process_usage.get("create_time"),
                        "cpu_time_seconds": process_usage.get("cpu_time_seconds"),
                    },
                    "resource_breakdown": resource_breakdown,
                    "battery_usage": battery_usage,
                    "network_stats": {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                    },
                    "reticulum_stats": {
                        "total_paths": total_paths,
                        "announces_per_second": announces_per_second,
                        "announces_per_minute": announces_per_minute,
                        "announces_per_hour": announces_per_hour,
                        **cache_stats(),
                        "memory_cleanup": getattr(
                            getattr(app, "memory_pressure", None),
                            "last_stats",
                            {},
                        ),
                    },
                    "is_reticulum_running": hasattr(app, "reticulum")
                    and app.reticulum is not None,
                    "download_stats": {
                        "avg_download_speed_bps": avg_download_speed_bps,
                    },
                    "emergency": getattr(app, "emergency", False),
                    "integrity_issues": getattr(app, "integrity_issues", []),
                    "database_health_issues": getattr(
                        app,
                        "database_health_issues",
                        [],
                    ),
                    "user_guidance": _safe_user_guidance(),
                    "tutorial_seen": _safe_config_get("tutorial_seen", "false")
                    == "true",
                    "changelog_seen_version": _safe_config_get(
                        "changelog_seen_version",
                        "0.0.0",
                    ),
                    "channel_prompt_seen": _safe_config_get(
                        "channel_prompt_seen",
                        "",
                    ),
                    "migration": dict(app.migration_context),
                },
            },
        )

    # get changelog

    # get changelog
    @routes.get("/api/v1/app/changelog")
    async def app_changelog(request):
        changelog_path = get_file_path("CHANGELOG.md")
        if not os.path.exists(changelog_path):
            # try in public folder
            changelog_path = get_file_path("public/CHANGELOG.md")

        if not os.path.exists(changelog_path):
            # try project root if not found in package
            changelog_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "CHANGELOG.md",
            )

        if not os.path.exists(changelog_path):
            fallback_markdown = (
                f"# MeshChatX {app_version}\n\n"
                "Changelog is unavailable in this build.\n\n"
                "Please check the project release page for full notes."
            )
            html_content = MarkdownRenderer.render(fallback_markdown)
            return web.json_response(
                {
                    "changelog": fallback_markdown,
                    "html": html_content,
                    "version": app_version,
                },
            )

        try:
            with open(changelog_path) as f:
                content = f.read()

            # Render markdown to HTML
            html_content = MarkdownRenderer.render(content)

            return web.json_response(
                {
                    "changelog": content,
                    "html": html_content,
                    "version": app_version,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # third-party dependency licenses (Python + Node)

    # third-party dependency licenses (Python + Node)
    @routes.get("/api/v1/licenses")
    async def licenses_list(_request):
        from meshchatx.src.backend.licenses_collector import build_licenses_payload

        try:
            payload = await asyncio.to_thread(build_licenses_payload)
            return web.json_response(payload)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # mark tutorial as seen
