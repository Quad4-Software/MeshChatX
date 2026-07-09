# SPDX-License-Identifier: 0BSD

import atexit
import errno
import os
import sys


class StorageLockError(OSError):
    pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _soft_lock_contested(other_pid: int | None) -> bool:
    """Whether a soft PID lock should block acquire.

    On platforms without flock (notably Android), process liveness probes are
    unreliable across app restarts, so only treat the *current* PID as held.
    Desktop soft-lock still uses kill(pid, 0) when flock is unsupported.
    """
    if other_pid is None:
        return False
    if other_pid == os.getpid():
        return True
    if sys.platform == "android" or "ANDROID_ROOT" in os.environ:
        return False
    return _pid_alive(other_pid)


def _flock_unsupported(exc: BaseException) -> bool:
    if isinstance(exc, NotImplementedError):
        return True
    if not isinstance(exc, OSError):
        return False
    unsupported = {errno.ENOSYS, errno.EOPNOTSUPP}
    if hasattr(errno, "ENOTSUP"):
        unsupported.add(errno.ENOTSUP)
    return exc.errno in unsupported


class StorageLock:
    def __init__(self, storage_dir: str):
        self.storage_dir = os.path.abspath(storage_dir)
        self.lock_path = os.path.join(self.storage_dir, ".meshchatx.lock")
        self._handle = None
        self._soft = False

    def acquire(self) -> None:
        os.makedirs(self.storage_dir, exist_ok=True)
        self._handle = open(self.lock_path, "a+b")
        try:
            if sys.platform == "win32":
                import msvcrt

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                try:
                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (OSError, NotImplementedError) as exc:
                    if not _flock_unsupported(exc):
                        raise
                    # Android and some filesystems do not implement flock.
                    self._acquire_soft()
                    self._soft = True
                    atexit.register(self.release)
                    return
        except StorageLockError:
            raise
        except OSError as exc:
            if self._handle is not None:
                self._handle.close()
                self._handle = None
            raise StorageLockError(
                f"Another MeshChatX instance is already using storage at {self.storage_dir}",
            ) from exc
        self._write_pid()
        atexit.register(self.release)

    def _acquire_soft(self) -> None:
        assert self._handle is not None
        self._handle.seek(0)
        raw = self._handle.read().strip()
        other_pid = None
        if raw:
            try:
                other_pid = int(raw.decode("ascii", errors="ignore").strip())
            except ValueError:
                other_pid = None
        if _soft_lock_contested(other_pid):
            self._handle.close()
            self._handle = None
            raise StorageLockError(
                f"Another MeshChatX instance is already using storage at {self.storage_dir}",
            )
        self._write_pid()

    def _write_pid(self) -> None:
        assert self._handle is not None
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(str(os.getpid()).encode())
        self._handle.flush()

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if self._soft:
                pass
            elif sys.platform == "win32":
                import msvcrt

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            if self._soft:
                try:
                    self._handle.seek(0)
                    self._handle.truncate()
                    self._handle.flush()
                except OSError:
                    pass
            self._handle.close()
        except OSError:
            pass
        self._handle = None
        self._soft = False
