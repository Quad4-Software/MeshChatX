// Package fsutil holds small filesystem helpers shared by the shell's
// state persistence code.
package fsutil

import (
	"os"
	"path/filepath"
)

// WriteFileAtomic writes data to path via a temp file in the same directory,
// fsyncs it, renames it over path and best-effort fsyncs the directory, so a
// crash mid-write cannot leave a truncated file behind.
func WriteFileAtomic(path string, data []byte, perm os.FileMode) error {
	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, "."+filepath.Base(path)+".tmp-*")
	if err != nil {
		return err
	}
	tmpName := tmp.Name()
	cleanup := func() {
		_ = tmp.Close()
		_ = os.Remove(tmpName)
	}
	if _, err := tmp.Write(data); err != nil {
		cleanup()
		return err
	}
	if err := tmp.Chmod(perm); err != nil {
		cleanup()
		return err
	}
	if err := tmp.Sync(); err != nil {
		cleanup()
		return err
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpName)
		return err
	}
	if err := os.Rename(tmpName, path); err != nil {
		_ = os.Remove(tmpName)
		return err
	}
	fsyncDir(dir)
	return nil
}

func fsyncDir(dir string) {
	if f, err := os.Open(dir); err == nil {
		_ = f.Sync()
		_ = f.Close()
	}
}
