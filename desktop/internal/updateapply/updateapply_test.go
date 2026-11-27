package updateapply

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func writeMarker(t *testing.T, storageDir string, marker map[string]any) {
	t.Helper()
	dir := filepath.Join(storageDir, "updates")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	data, _ := json.Marshal(marker)
	if err := os.WriteFile(filepath.Join(dir, "pending.json"), data, 0o644); err != nil {
		t.Fatal(err)
	}
}

func sha256Sum(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func TestApplyPendingUpdateNoMarker(t *testing.T) {
	res := ApplyPendingUpdate(t.TempDir())
	if res["applied"] != false || res["error"] != "no_pending_update" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingUpdateBadMarker(t *testing.T) {
	dir := t.TempDir()
	// path escape attempt: file contains a separator
	writeMarker(t, dir, map[string]any{
		"file": "../evil", "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
		"kind": "appimage",
	})
	if res := ApplyPendingUpdate(dir); res["error"] != "bad_pending_marker" {
		t.Fatalf("res: %v", res)
	}
	// bad sha format
	writeMarker(t, dir, map[string]any{"file": "x.AppImage", "sha256": "zz", "kind": "appimage"})
	if res := ApplyPendingUpdate(dir); res["error"] != "bad_pending_marker" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingUpdateUnsupportedKind(t *testing.T) {
	dir := t.TempDir()
	writeMarker(t, dir, map[string]any{
		"file":   "x.AppImage",
		"sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
		"kind":   "deb",
	})
	res := ApplyPendingUpdate(dir)
	if res["error"] != "unsupported_kind" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingUpdateNotAppImage(t *testing.T) {
	dir := t.TempDir()
	pending := filepath.Join(dir, "updates", "pending")
	if err := os.MkdirAll(pending, 0o755); err != nil {
		t.Fatal(err)
	}
	staged := filepath.Join(pending, "new.AppImage")
	if err := os.WriteFile(staged, []byte("new-content"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeMarker(t, dir, map[string]any{
		"file": "new.AppImage", "sha256": sha256Sum(t, staged), "kind": "appimage",
	})
	// APPIMAGE unset -> not_appimage
	os.Unsetenv("APPIMAGE")
	if res := ApplyPendingUpdate(dir); res["error"] != "not_appimage" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingUpdateSuccess(t *testing.T) {
	dir := t.TempDir()
	pending := filepath.Join(dir, "updates", "pending")
	if err := os.MkdirAll(pending, 0o755); err != nil {
		t.Fatal(err)
	}
	staged := filepath.Join(pending, "new.AppImage")
	if err := os.WriteFile(staged, []byte("new-content"), 0o644); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(t.TempDir(), "MeshChatX.AppImage")
	if err := os.WriteFile(target, []byte("old-content"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeMarker(t, dir, map[string]any{
		"file": "new.AppImage", "sha256": sha256Sum(t, staged), "kind": "appimage",
	})
	t.Setenv("APPIMAGE", target)

	res := ApplyPendingUpdate(dir)
	if res["applied"] != true {
		t.Fatalf("res: %v", res)
	}
	data, _ := os.ReadFile(target)
	if string(data) != "new-content" {
		t.Fatalf("target content: %q", data)
	}
	// backup of old target exists
	if _, err := os.Stat(target + ".bak"); err != nil {
		t.Fatal("backup missing")
	}
	// pending marker cleared
	if _, err := os.Stat(filepath.Join(dir, "updates", "pending.json")); !os.IsNotExist(err) {
		t.Fatal("pending marker not cleared")
	}
}

func TestApplyPendingUpdateShaMismatch(t *testing.T) {
	dir := t.TempDir()
	pending := filepath.Join(dir, "updates", "pending")
	if err := os.MkdirAll(pending, 0o755); err != nil {
		t.Fatal(err)
	}
	staged := filepath.Join(pending, "new.AppImage")
	if err := os.WriteFile(staged, []byte("new-content"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeMarker(t, dir, map[string]any{
		"file":   "new.AppImage",
		"sha256": "0000000000000000000000000000000000000000000000000000000000000000",
		"kind":   "appimage",
	})
	target := filepath.Join(t.TempDir(), "MeshChatX.AppImage")
	if err := os.WriteFile(target, []byte("old"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("APPIMAGE", target)
	res := ApplyPendingUpdate(dir)
	if res["error"] != "sha256_mismatch" {
		t.Fatalf("res: %v", res)
	}
	// target untouched
	data, _ := os.ReadFile(target)
	if string(data) != "old" {
		t.Fatal("target modified on mismatch")
	}
}

func TestSameFile(t *testing.T) {
	dir := t.TempDir()
	real := filepath.Join(dir, "f.bin")
	if err := os.WriteFile(real, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(dir, "l.bin")
	if err := os.Symlink(real, link); err != nil {
		t.Skipf("symlink: %v", err)
	}
	if !sameFile(real, link) {
		t.Fatal("symlinked path not detected as same file")
	}
	if !sameFile(real, filepath.Join(dir, "sub", "..", "f.bin")) {
		t.Fatal("dotdot path not detected as same file")
	}
	if sameFile(real, filepath.Join(dir, "other.bin")) {
		t.Fatal("distinct files reported same")
	}
}

func TestCopyFileSync(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "src.bin")
	dst := filepath.Join(dir, "dst.bin")
	payload := []byte("payload-bytes")
	if err := os.WriteFile(src, payload, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := copyFileSync(src, dst); err != nil {
		t.Fatalf("copyFileSync: %v", err)
	}
	got, err := os.ReadFile(dst)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(payload) {
		t.Fatalf("copied %q", got)
	}
}

func TestSha256FileOnDirectoryReturnsError(t *testing.T) {
	if got, err := sha256File(t.TempDir()); err == nil {
		t.Fatalf("expected error hashing a directory, got hash %q", got)
	}
}

func TestReplaceFileByCopyPreservesExecutableMode(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "src.bin")
	dst := filepath.Join(dir, "dst.bin")
	if err := os.WriteFile(src, []byte("new-payload"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(dst, []byte("old"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := replaceFileByCopy(src, dst, 0o755); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(dst)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "new-payload" {
		t.Fatalf("dst content = %q", data)
	}
	info, err := os.Stat(dst)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o755 {
		t.Fatalf("dst mode = %o", info.Mode().Perm())
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	for _, e := range entries {
		if filepath.Base(e.Name()) != e.Name() || len(e.Name()) == 0 {
			continue
		}
		if filepath.Ext(e.Name()) == "" && e.Name() != "src.bin" && e.Name() != "dst.bin" {
			t.Fatalf("temp sibling leaked: %s", e.Name())
		}
	}
}

func TestReplaceFileByCopyMissingDestDir(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "src.bin")
	if err := os.WriteFile(src, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	err := replaceFileByCopy(src, filepath.Join(dir, "no-such-dir", "dst.bin"), 0o755)
	if err == nil {
		t.Fatal("expected error for missing destination dir")
	}
}
