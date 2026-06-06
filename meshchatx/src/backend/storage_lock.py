# SPDX-License-Identifier: 0BSD

import atexit
import os
import sys


class StorageLockError(OSError):
    pass


class StorageLock:
    def __init__(self, storage_dir: str):
        self.storage_dir = os.path.abspath(storage_dir)
        self.lock_path = os.path.join(self.storage_dir, ".meshchatx.lock")
        self._handle = None

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

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._handle.close()
            self._handle = None
            raise StorageLockError(
                f"Another MeshChatX instance is already using storage at {self.storage_dir}",
            ) from exc
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(str(os.getpid()).encode())
        self._handle.flush()
        atexit.register(self.release)

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            self._handle.close()
        except OSError:
            pass
        self._handle = None
