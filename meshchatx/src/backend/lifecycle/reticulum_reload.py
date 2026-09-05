# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: reload_reticulum."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


async def reload_reticulum_instance(app: Any):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    g = mc.__dict__
    for _k in (
        "LXMF",
        "RNS",
        "AsyncUtils",
        "InterfaceEditor",
        "InterfaceConfigParser",
        "web",
        "json",
        "logger",
        "logging",
        "os",
        "sys",
        "time",
        "asyncio",
        "traceback",
        "copy",
        "shutil",
        "tempfile",
        "threading",
        "base64",
        "configparser",
        "sqlite3",
        "secrets",
        "re",
        "io",
        "contextlib",
        "datetime",
        "platform",
        "cast",
        "UTC",
    ):
        if _k in g:
            globals()[_k] = g[_k]
    print("Hot reloading Reticulum stack...")
    # Keep reference to old reticulum instance for cleanup
    old_reticulum = getattr(app, "reticulum", None)
    identity_to_restore = app.identity
    identity_hashes = []
    for ctx in list(app.contexts.values()):
        with contextlib.suppress(Exception):
            identity_hashes.append(ctx.identity.hash)
    if not identity_hashes:
        identity_hash = getattr(identity_to_restore, "hash", None)
        if identity_hash:
            identity_hashes.append(identity_hash)

    try:
        if identity_to_restore is None:
            raise RuntimeError(
                "Cannot reload Reticulum without an active identity context.",
            )
        await app._send_rns_reload_status(
            "starting",
            "Reloading RNS stack...",
        )

        # Signal background loops to exit
        app._identity_session_id += 1
        app._network_ready = False

        await app._send_rns_reload_status(
            "stopping-services",
            "Stopping bots and mesh services across identities...",
        )
        app._teardown_all_contexts_for_reload()

        # Give loops a moment to finish
        await asyncio.sleep(2)

        await app._send_rns_reload_status(
            "deregistering",
            "Deregistering destinations and active links...",
        )
        for identity_hash in identity_hashes:
            app.cleanup_rns_state_for_identity(identity_hash)

        # Close RNS instance first to let it detach interfaces naturally
        await app._send_rns_reload_status(
            "detaching",
            "Detaching interfaces and shutting down Reticulum...",
        )
        try:
            # Use class method to ensure all instances are cleaned up if any
            RNS.Reticulum.exit_handler()
        except Exception as e:
            print(f"Warning during RNS exit: {e}")

        # Aggressively close RNS interfaces to release sockets if they didn't close
        try:
            interfaces = []
            if hasattr(RNS.Transport, "interfaces"):
                interfaces.extend(RNS.Transport.interfaces)
            if hasattr(RNS.Transport, "local_client_interfaces"):
                interfaces.extend(RNS.Transport.local_client_interfaces)

            for interface in interfaces:
                try:
                    # Generic socketserver shutdown
                    if hasattr(interface, "server") and interface.server:
                        try:
                            interface.server.shutdown()
                            interface.server.server_close()
                        except Exception:
                            pass

                    # AutoInterface specific
                    if hasattr(interface, "interface_servers"):
                        for server in interface.interface_servers.values():
                            try:
                                server.shutdown()
                                server.server_close()
                            except Exception:
                                pass

                    # For LocalServerInterface which Reticulum doesn't close properly
                    if hasattr(interface, "server") and interface.server:
                        try:
                            interface.server.shutdown()
                            interface.server.server_close()
                        except Exception:
                            pass

                    # TCPClientInterface/etc
                    if hasattr(interface, "socket") and interface.socket:
                        try:
                            # Check if socket is still valid before shutdown
                            if (
                                hasattr(interface.socket, "fileno")
                                and interface.socket.fileno() != -1
                            ):
                                try:
                                    interface.socket.shutdown(socket.SHUT_RDWR)
                                except Exception:
                                    pass
                                try:
                                    interface.socket.close()
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    interface.detach()
                    interface.detached = True
                except Exception as e:
                    print(f"Warning closing interface during reload: {e}")
        except Exception as e:
            print(f"Warning during aggressive interface cleanup: {e}")

        if old_reticulum:
            rpc_listener_names = [
                "rpc_listener",
                "_Reticulum__rpc_listener",
                "_rpc_listener",
            ]
            for attr_name in rpc_listener_names:
                if hasattr(old_reticulum, attr_name):
                    listener = getattr(old_reticulum, attr_name)
                    if listener:
                        try:
                            print(
                                f"Forcing closure of RPC listener in {attr_name}...",
                            )
                            app._force_close_listener(listener)
                            setattr(old_reticulum, attr_name, None)
                        except Exception as e:
                            print(f"Warning closing RPC listener {attr_name}: {e}")

        # Clear RNS singleton and internal state to allow re-initialization
        try:
            # Reticulum uses private variables for singleton and state control
            # We need to clear them so we can create a new instance
            if hasattr(RNS.Reticulum, "_Reticulum__instance"):
                # Keep the instance object until we're done waiting for sockets.
                # Some Reticulum background workers still consult get_instance().
                pass
            if hasattr(RNS.Reticulum, "_Reticulum__exit_handler_ran"):
                RNS.Reticulum._Reticulum__exit_handler_ran = False
            if hasattr(RNS.Reticulum, "_Reticulum__interface_detach_ran"):
                RNS.Reticulum._Reticulum__interface_detach_ran = False

            app._reset_transport_globals_for_reload()
            clear_all_cached_links()
            clear_all_nomadnet_cached_links()

            # Clear Identity globals
            RNS.Identity.known_destinations = {}
            RNS.Identity.known_ratchets = {}

            # Unregister old exit handlers from atexit if possible
            try:
                # Reticulum uses a staticmethod exit_handler
                atexit.unregister(RNS.Reticulum.exit_handler)
            except Exception:
                pass

        except Exception as e:
            print(f"Warning clearing RNS state: {e}")

        # Remove reticulum instance from app
        if hasattr(app, "reticulum"):
            del app.reticulum

        print("Waiting for ports to settle...")
        await asyncio.sleep(4)

        # Detect RPC type from reticulum instance if possible, otherwise default to both
        rpc_addrs = []
        if old_reticulum:
            if hasattr(old_reticulum, "rpc_addr") and old_reticulum.rpc_addr:
                rpc_addrs.append(
                    (
                        old_reticulum.rpc_addr,
                        getattr(old_reticulum, "rpc_type", "AF_INET"),
                    ),
                )

        # Also check the config file for ports
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
                else:
                    if cp.has_section("reticulum"):
                        rpc_port = cp.getint(
                            "reticulum",
                            "rpc_port",
                            fallback=37429,
                        )
                        rpc_bind = cp.get(
                            "reticulum",
                            "rpc_bind",
                            fallback="127.0.0.1",
                        )
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

                        # Only add if not already there
                        if not any(
                            addr == (rpc_bind, rpc_port) for addr, _ in rpc_addrs
                        ):
                            rpc_addrs.append(((rpc_bind, rpc_port), "AF_INET"))
                        if not any(
                            addr == (shared_bind, shared_port) for addr, _ in rpc_addrs
                        ):
                            rpc_addrs.append(
                                ((shared_bind, shared_port), "AF_INET"),
                            )
        except Exception as e:
            print(f"Warning reading Reticulum config for ports: {e}")

        if not rpc_addrs:
            rpc_addrs.append((("127.0.0.1", 37429), "AF_INET"))
            rpc_addrs.append((("127.0.0.1", 37428), "AF_INET"))

        abstract_unix_addr_in_use_after_wait = False
        reload_probe_attempts = 3
        for i in range(reload_probe_attempts):
            all_free = True
            for addr, family_str in rpc_addrs:
                try:
                    family = (
                        socket.AF_INET if family_str == "AF_INET" else socket.AF_UNIX
                    )
                    s = socket.socket(family, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    try:
                        # Use SO_REUSEADDR to check if we can actually bind
                        if family == socket.AF_INET:
                            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.bind(addr)
                        s.close()
                    except OSError:
                        addr_display = addr
                        if (
                            family == socket.AF_UNIX
                            and isinstance(addr, str)
                            and addr.startswith("\0")
                        ):
                            addr_display = addr[1:] + " (abstract)"

                        print(
                            f"RPC addr {addr_display} still in use... (attempt {i + 1}/{reload_probe_attempts})",
                        )
                        s.close()
                        is_abstract_unix_addr = (
                            family == socket.AF_UNIX
                            and isinstance(addr, str)
                            and addr.startswith("\0")
                        )
                        if is_abstract_unix_addr:
                            released = False
                            if app._force_close_abstract_unix_addr(addr):
                                try:
                                    s2 = socket.socket(
                                        socket.AF_UNIX,
                                        socket.SOCK_STREAM,
                                    )
                                    try:
                                        s2.bind(addr)
                                        s2.close()
                                        print(
                                            f"Released abstract RPC addr {addr_display} from this process.",
                                        )
                                        released = True
                                    except OSError:
                                        s2.close()
                                except Exception:
                                    pass

                            if released:
                                continue

                            all_free = False
                            continue

                        all_free = False

                        # If we are stuck, try to force close the connection manually
                        if i > 1:
                            try:
                                current_process = psutil.Process()
                                # We use kind='all' to catch both TCP and UNIX sockets
                                for conn in current_process.net_connections(
                                    kind="all",
                                ):
                                    try:
                                        match = False
                                        if conn.laddr:
                                            if family_str == "AF_INET" and isinstance(
                                                conn.laddr, tuple
                                            ):
                                                # Match IP and port for IPv4
                                                if conn.laddr.port == addr[1] and (
                                                    conn.laddr.ip == addr[0]
                                                    or addr[0] == "0.0.0.0"
                                                ):
                                                    match = True
                                            elif family_str == "AF_UNIX":
                                                # Match path for UNIX sockets, including abstract
                                                # Psutil sometimes returns abstract addresses as strings or bytes,
                                                # with or without the leading null byte.
                                                laddr = conn.laddr

                                                # Normalize both to bytes for comparison
                                                target_addr = (
                                                    addr
                                                    if isinstance(addr, bytes)
                                                    else addr.encode()
                                                    if isinstance(addr, str)
                                                    else b""
                                                )
                                                current_laddr = (
                                                    laddr
                                                    if isinstance(laddr, bytes)
                                                    else laddr.encode()
                                                    if isinstance(laddr, str)
                                                    else b""
                                                )

                                                if (
                                                    current_laddr == target_addr
                                                    or (
                                                        target_addr.startswith(
                                                            b"\0",
                                                        )
                                                        and current_laddr
                                                        == target_addr[1:]
                                                    )
                                                    or (
                                                        current_laddr.startswith(
                                                            b"\0",
                                                        )
                                                        and target_addr
                                                        == current_laddr[1:]
                                                    )
                                                ):
                                                    match = True
                                                elif (
                                                    target_addr in current_laddr
                                                    or current_laddr in target_addr
                                                ):
                                                    # Last resort: partial match
                                                    if (
                                                        len(target_addr) > 5
                                                        and len(current_laddr) > 5
                                                    ):
                                                        match = True

                                        if match:
                                            # If we found a match, force close the file descriptor
                                            # to tell the OS to release the socket immediately.
                                            status_str = getattr(
                                                conn,
                                                "status",
                                                "UNKNOWN",
                                            )
                                            print(
                                                f"Force closing lingering {family_str} connection {conn.laddr} (status: {status_str})",
                                            )

                                            try:
                                                if (
                                                    hasattr(conn, "fd")
                                                    and conn.fd != -1
                                                ):
                                                    try:
                                                        os.close(conn.fd)
                                                    except Exception as fd_err:
                                                        print(
                                                            f"Failed to close FD {getattr(conn, 'fd', 'N/A')}: {fd_err}",
                                                        )
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            except Exception as e:
                                print(
                                    f"Error during manual RPC connection kill: {e}",
                                )

                        break
                except Exception as e:
                    print(f"Error checking RPC addr {addr}: {e}")

            if all_free:
                print("All RNS ports/sockets are free.")
                break

            await asyncio.sleep(1)

        if not all_free:
            await asyncio.sleep(2)
            for addr, family_str in rpc_addrs:
                if (
                    family_str == "AF_UNIX"
                    and isinstance(addr, str)
                    and addr.startswith("\0")
                ):
                    with contextlib.suppress(Exception):
                        app._force_close_abstract_unix_addr(addr)

            last_check_all_free = True
            for addr, family_str in rpc_addrs:
                try:
                    family = (
                        socket.AF_INET if family_str == "AF_INET" else socket.AF_UNIX
                    )
                    s = socket.socket(family, socket.SOCK_STREAM)
                    try:
                        s.bind(addr)
                        s.close()
                    except OSError:
                        s.close()
                        is_abstract = (
                            family == socket.AF_UNIX
                            and isinstance(addr, str)
                            and addr.startswith("\0")
                        )
                        if is_abstract:
                            abstract_unix_addr_in_use_after_wait = True
                            continue
                        last_check_all_free = False
                        break
                    except Exception:
                        pass
                except Exception:
                    pass

            if not last_check_all_free:
                raise OSError(
                    "Timeout waiting for RNS ports to be released. Cannot restart.",
                )
            print("RNS ports finally free after last-second check.")

        gc.collect()

        if hasattr(RNS.Reticulum, "_Reticulum__instance"):
            RNS.Reticulum._Reticulum__instance = None

        switched_instance_name = None
        instance_restore_name = None
        if abstract_unix_addr_in_use_after_wait:
            stored_instance_name = app._read_reticulum_instance_name()
            stable_base = ReticulumMeshChat._strip_reload_instance_suffix(
                stored_instance_name,
            )
            instance_restore_name = (
                stable_base if stable_base is not None else "default"
            )
            switched_instance_name = (
                f"{instance_restore_name}-reload-{os.getpid()}-{int(time.time())}"
            )
            app._write_reticulum_instance_name(switched_instance_name)
            print(
                "Abstract UNIX RPC address remained busy. "
                f"Retrying with temporary instance_name={switched_instance_name}",
            )

        app.running = True
        await app._send_rns_reload_status(
            "starting-services",
            "Starting identity services again...",
        )
        try:
            app.setup_identity(identity_to_restore)
        finally:
            if switched_instance_name:
                app._write_reticulum_instance_name(instance_restore_name)
        app._mark_network_ready()
        app._finish_deferred_startup_services()
        await app._send_rns_reload_status(
            "done",
            "RNS reload complete.",
            level="success",
            in_progress=False,
        )

        return True
    except Exception as e:
        print(f"Hot reload failed: {e}")

        traceback.print_exc()
        await app._send_rns_reload_status(
            "failed",
            f"RNS reload failed: {e!s}",
            level="error",
            in_progress=False,
        )

        # Try to recover if possible without wiping storage.
        if not hasattr(app, "reticulum") and identity_to_restore is not None:
            try:
                app.setup_identity(identity_to_restore)
                app._mark_network_ready()
                app._finish_deferred_startup_services()
                return False
            except Exception as recover_exc:
                app._mark_network_degraded(
                    f"RNS reload failed and recovery failed: {recover_exc}",
                )
        else:
            app._mark_network_degraded(f"RNS reload failed: {e}")

        return False
