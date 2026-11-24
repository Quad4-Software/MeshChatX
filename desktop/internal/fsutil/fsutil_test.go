package fsutil

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestWriteFileAtomicReplaces(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	if err := WriteFileAtomic(path, []byte("one"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := WriteFileAtomic(path, []byte("two"), 0o644); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil || string(data) != "two" {
		t.Fatalf("got %q err %v", data, err)
	}
	entries, _ := os.ReadDir(dir)
	for _, e := range entries {
		if e.Name() != "state.json" {
			t.Fatalf("leftover temp file %q", e.Name())
		}
	}
}

func TestWriteFileAtomicFailureKeepsOld(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	if err := WriteFileAtomic(path, []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(dir, 0o555); err != nil {
		t.Fatal(err)
	}
	defer os.Chmod(dir, 0o755)
	if err := WriteFileAtomic(path, []byte("new"), 0o644); err == nil {
		t.Fatal("expected error writing into unwritable dir")
	}
	data, err := os.ReadFile(path)
	if err != nil || string(data) != "old" {
		t.Fatalf("old file damaged: %q err %v", data, err)
	}
}

func TestWriteFileAtomicPerms(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("posix perms")
	}
	dir := t.TempDir()
	path := filepath.Join(dir, "secret.json")
	if err := WriteFileAtomic(path, []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("perm = %o", info.Mode().Perm())
	}
}
