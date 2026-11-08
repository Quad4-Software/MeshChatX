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
