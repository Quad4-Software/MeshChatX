package updater

import (
	"archive/tar"
	"archive/zip"
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// The apply path is gated behind the rollout flag; tests opt in via env.
func TestMain(m *testing.M) {
	os.Setenv("MESHCHATX_UPDATE_ROLLOUT", "1")
	os.Exit(m.Run())
}

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

// stageFile writes a staged artifact into updates/pending and returns its
// path plus the marker fields matching a real backend marker.
func stageFile(t *testing.T, storageDir, name string, content []byte) (string, map[string]any) {
	t.Helper()
	pending := filepath.Join(storageDir, "updates", "pending")
	if err := os.MkdirAll(pending, 0o755); err != nil {
		t.Fatal(err)
	}
	p := filepath.Join(pending, name)
	if err := os.WriteFile(p, content, 0o644); err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(content)
	sha := hex.EncodeToString(sum[:])
	return p, map[string]any{
		"version":      1,
		"file":         name,
		"sha256":       sha,
		"size":         len(content),
		"apply_policy": "manual",
		"artifacts": []any{
			map[string]any{
				"file": name, "sha256": sha, "size": len(content),
			},
		},
	}
}

func pendingGone(t *testing.T, storageDir string) {
	t.Helper()
	if _, err := os.Stat(filepath.Join(storageDir, "updates", "pending.json")); !os.IsNotExist(err) {
		t.Fatal("pending marker not cleared")
	}
}

// makeInstallDir builds a fake portable install dir with the self-updatable
// marker plus a couple of payload files.
func makeInstallDir(t *testing.T) string {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "MeshChatX-portable")
	if err := os.MkdirAll(filepath.Join(dir, "backend"), 0o755); err != nil {
		t.Fatal(err)
	}
	for name, content := range map[string]string{
		"meshchatx-desktop":   "old-shell",
		"backend/backend-bin": "old-backend",
		updatableMarkerName:   "portable",
	} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

func makeTarGz(t *testing.T, files map[string]string) []byte {
	t.Helper()
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	tw := tar.NewWriter(gz)
	for name, content := range files {
		if err := tw.WriteHeader(&tar.Header{
			Name: name, Mode: 0o755, Size: int64(len(content)), Typeflag: tar.TypeReg,
		}); err != nil {
			t.Fatal(err)
		}
		if _, err := tw.Write([]byte(content)); err != nil {
			t.Fatal(err)
		}
	}
	if err := tw.Close(); err != nil {
		t.Fatal(err)
	}
	if err := gz.Close(); err != nil {
		t.Fatal(err)
	}
	return buf.Bytes()
}

func makeZip(t *testing.T, files map[string]string) []byte {
	t.Helper()
	var buf bytes.Buffer
	zw := zip.NewWriter(&buf)
	for name, content := range files {
		w, err := zw.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := w.Write([]byte(content)); err != nil {
			t.Fatal(err)
		}
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	return buf.Bytes()
}

// ---- marker / verification failures --------------------------------------

func TestApplyPendingNoMarker(t *testing.T) {
	res := ApplyPending(t.TempDir())
	if res["applied"] != false || res["error"] != "no_pending_update" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingBadMarker(t *testing.T) {
	dir := t.TempDir()
	writeMarker(t, dir, map[string]any{
		"file": "../evil", "kind": "appimage",
		"sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
	})
	if res := ApplyPending(dir); res["error"] != "bad_pending_marker" {
		t.Fatalf("res: %v", res)
	}
	writeMarker(t, dir, map[string]any{"file": "x.deb", "sha256": "zz", "kind": "deb"})
	if res := ApplyPending(dir); res["error"] != "bad_pending_marker" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingStagedMissing(t *testing.T) {
	dir := t.TempDir()
	writeMarker(t, dir, map[string]any{
		"file": "x.deb", "kind": "deb",
		"sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
	})
	if res := ApplyPending(dir); res["error"] != "staged_missing" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingShaMismatch(t *testing.T) {
	dir := t.TempDir()
	if _, err := os.Stat(filepath.Join(dir, "updates")); err == nil {
		t.Fatal("unexpected updates dir")
	}
	staged, marker := stageFile(t, dir, "new.deb", []byte("pkg-bytes"))
	marker["kind"] = "deb"
	marker["sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
	marker["artifacts"] = []any{
		map[string]any{
			"file":   "new.deb",
			"sha256": "0000000000000000000000000000000000000000000000000000000000000000",
			"size":   9,
		},
	}
	writeMarker(t, dir, marker)
	res := ApplyPending(dir)
	if res["error"] != "sha256_mismatch" {
		t.Fatalf("res: %v", res)
	}
	// staged file still present: nothing consumed on refusal
	if _, err := os.Stat(staged); err != nil {
		t.Fatal("staged file removed on sha mismatch")
	}
}

func TestApplyPendingSizeMismatch(t *testing.T) {
	dir := t.TempDir()
	staged, marker := stageFile(t, dir, "new.deb", []byte("pkg-bytes"))
	marker["kind"] = "deb"
	marker["artifacts"] = []any{
		map[string]any{"file": "new.deb", "sha256": marker["sha256"], "size": 999},
	}
	writeMarker(t, dir, marker)
	res := ApplyPending(dir)
	if res["error"] != "size_mismatch" {
		t.Fatalf("res: %v", res)
	}
	if _, err := os.Stat(staged); err != nil {
		t.Fatal("staged file removed on size mismatch")
	}
}

func TestApplyPendingPlatformMismatch(t *testing.T) {
	dir := t.TempDir()
	_, marker := stageFile(t, dir, "new.deb", []byte("pkg-bytes"))
	marker["kind"] = "deb"
	marker["platform"] = map[string]string{
		"linux": "windows", "windows": "linux", "darwin": "linux",
	}[runtime.GOOS]
	if marker["platform"] == nil {
		marker["platform"] = "windows"
	}
	writeMarker(t, dir, marker)
	if res := ApplyPending(dir); res["error"] != "platform_mismatch" {
		t.Fatalf("res: %v", res)
	}
}

func TestApplyPendingArtifactShaConflict(t *testing.T) {
	dir := t.TempDir()
	_, marker := stageFile(t, dir, "new.deb", []byte("pkg-bytes"))
	marker["kind"] = "deb"
	marker["artifacts"] = []any{
		map[string]any{
			"file":   "new.deb",
			"sha256": "1111111111111111111111111111111111111111111111111111111111111111",
			"size":   9,
		},
	}
	writeMarker(t, dir, marker)
	if res := ApplyPending(dir); res["error"] != "bad_pending_marker" {
		t.Fatalf("res: %v", res)
	}
}

// ---- appimage delegation --------------------------------------------------

func TestApplyPendingAppImage(t *testing.T) {
	dir := t.TempDir()
	_, marker := stageFile(t, dir, "new.AppImage", []byte("new-content"))
	marker["kind"] = "appimage"
	writeMarker(t, dir, marker)
	target := filepath.Join(t.TempDir(), "MeshChatX.AppImage")
	if err := os.WriteFile(target, []byte("old-content"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("APPIMAGE", target)
	res := ApplyPending(dir)
	if res["applied"] != true || res["mode"] != "relaunch" || res["kind"] != "appimage" {
		t.Fatalf("res: %v", res)
	}
	data, _ := os.ReadFile(target)
	if string(data) != "new-content" {
		t.Fatalf("target content: %q", data)
	}
	if _, err := os.Stat(target + ".bak"); err != nil {
		t.Fatal("backup missing")
	}
	pendingGone(t, dir)
}

// ---- manual / external reporting ------------------------------------------

func TestApplyPendingManualKinds(t *testing.T) {
	cases := []struct {
		kind        string
		file        string
		wantMode    string
		wantInstrRe string
	}{
		{"deb", "MeshChatX.deb", "manual", "dpkg"},
		{"rpm", "MeshChatX.rpm", "manual", "rpm"},
		{"dmg", "MeshChatX.dmg", "manual", "DMG"},
		{"apk", "MeshChatX.apk", "manual", "APK"},
		{"wheel", "meshchatx-1.0-py3-none-any.whl", "manual", "pip install"},
		{"pyz", "meshchatx.pyz", "manual", "pip install"},
		{"oci", "meshchatx-oci.txt", "external", "docker pull"},
		{"flatpak", "meshchatx.flatpak", "external", "flatpak update"},
		{"other", "MeshChatX.msi.bin", "manual", "package manager"},
	}
	for _, tc := range cases {
		t.Run(tc.kind, func(t *testing.T) {
			dir := t.TempDir()
			staged, marker := stageFile(t, dir, tc.file, []byte("pkg-bytes"))
			marker["kind"] = tc.kind
			writeMarker(t, dir, marker)
			res := ApplyPending(dir)
			if res["applied"] != false {
				t.Fatalf("res: %v", res)
			}
			if res["mode"] != tc.wantMode {
				t.Fatalf("mode: %v", res)
			}
			if res["error"] != nil {
				t.Fatalf("unexpected error: %v", res)
			}
			instr, _ := res["instructions"].(string)
			if !strings.Contains(instr, tc.wantInstrRe) {
				t.Fatalf("instructions %q missing %q", instr, tc.wantInstrRe)
			}
			if tc.wantMode == "manual" && res["path"] != staged {
				t.Fatalf("path: %v", res)
			}
			// manual/external reporting never clears the marker or the file
			if _, err := os.Stat(staged); err != nil {
				t.Fatal("staged file removed on manual report")
			}
		})
	}
}

// ---- portable install-dir swap -------------------------------------------

func TestApplyPendingTarballDirSwap(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	payload := makeTarGz(t, map[string]string{
		"meshchatx-desktop-portable/meshchatx-desktop":   "new-shell",
		"meshchatx-desktop-portable/backend/backend-bin": "new-backend",
	})
	staged, marker := stageFile(t, dir, "MeshChatX-linux.tar.gz", payload)
	marker["kind"] = "tarball"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != true || res["mode"] != "relaunch" {
		t.Fatalf("res: %v", res)
	}
	got, err := os.ReadFile(filepath.Join(installDir, "meshchatx-desktop"))
	if err != nil || string(got) != "new-shell" {
		t.Fatalf("swapped shell: %q err=%v", got, err)
	}
	got, err = os.ReadFile(filepath.Join(installDir, "backend", "backend-bin"))
	if err != nil || string(got) != "new-backend" {
		t.Fatalf("swapped backend: %q err=%v", got, err)
	}
	// backup holds the old install
	got, err = os.ReadFile(filepath.Join(installDir+".bak", "meshchatx-desktop"))
	if err != nil || string(got) != "old-shell" {
		t.Fatalf("backup shell: %q err=%v", got, err)
	}
	// the self-updatable marker was carried forward
	if _, err := os.Stat(filepath.Join(installDir, updatableMarkerName)); err != nil {
		t.Fatal("updatable marker missing after swap")
	}
	// staged archive consumed, marker cleared
	if _, err := os.Stat(staged); !os.IsNotExist(err) {
		t.Fatal("staged archive not removed after apply")
	}
	pendingGone(t, dir)
}

func TestApplyPendingZipDirSwap(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	payload := makeZip(t, map[string]string{
		"portable/meshchatx-desktop.exe":   "new-shell",
		"portable/backend/backend-bin.exe": "new-backend",
		"portable/" + updatableMarkerName:  "portable",
	})
	// The backend normalizes the manifest "zip" kind to "other".
	_, marker := stageFile(t, dir, "MeshChatX-win32-x64.zip", payload)
	marker["kind"] = "other"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != true {
		t.Fatalf("res: %v", res)
	}
	got, err := os.ReadFile(filepath.Join(installDir, "meshchatx-desktop.exe"))
	if err != nil || string(got) != "new-shell" {
		t.Fatalf("swapped shell: %q err=%v", got, err)
	}
	if _, err := os.Stat(filepath.Join(installDir + ".bak")); err != nil {
		t.Fatal("backup dir missing")
	}
	pendingGone(t, dir)
}

func TestApplyPendingExeDirSwap(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	// An "exe"-kind artifact whose payload is an archive gets the dir swap.
	payload := makeZip(t, map[string]string{
		"meshchatx-desktop.exe": "new-shell",
	})
	_, marker := stageFile(t, dir, "MeshChatX-update.exe", payload)
	marker["kind"] = "exe"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != true {
		t.Fatalf("res: %v", res)
	}
	got, err := os.ReadFile(filepath.Join(installDir, "meshchatx-desktop.exe"))
	if err != nil || string(got) != "new-shell" {
		t.Fatalf("swapped shell: %q err=%v", got, err)
	}
}

func TestApplyPendingPortableNotSelfUpdatable(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	// remove the packaging marker -> the dir is not self-updatable
	if err := os.Remove(filepath.Join(installDir, updatableMarkerName)); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	payload := makeTarGz(t, map[string]string{"pkg/file": "new"})
	staged, marker := stageFile(t, dir, "MeshChatX-linux.tar.gz", payload)
	marker["kind"] = "tarball"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != false || res["mode"] != "manual" || res["reason"] != "not_self_updatable" {
		t.Fatalf("res: %v", res)
	}
	got, _ := os.ReadFile(filepath.Join(installDir, "meshchatx-desktop"))
	if string(got) != "old-shell" {
		t.Fatal("install dir modified without updatable marker")
	}
	if _, err := os.Stat(staged); err != nil {
		t.Fatal("staged file removed on manual report")
	}
}

func TestApplyPendingPortableNonArchivePayload(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	// MZ-magic installer bytes: not extractable in-process.
	staged, marker := stageFile(t, dir, "MeshChatX-installer.exe", []byte{'M', 'Z', 0x90, 0x00})
	marker["kind"] = "exe"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != false || res["mode"] != "manual" || res["reason"] != "payload_not_extractable" {
		t.Fatalf("res: %v", res)
	}
	if _, err := os.Stat(staged); err != nil {
		t.Fatal("staged file removed on manual report")
	}
}

func TestApplyPendingZipSlipRejected(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	var buf bytes.Buffer
	zw := zip.NewWriter(&buf)
	w, err := zw.Create("../escape.txt")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.Write([]byte("evil")); err != nil {
		t.Fatal(err)
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	_, marker := stageFile(t, dir, "evil.zip", buf.Bytes())
	marker["kind"] = "other"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != false {
		t.Fatalf("res: %v", res)
	}
	errStr, _ := res["error"].(string)
	if !strings.HasPrefix(errStr, "extract_failed") {
		t.Fatalf("expected extract_failed, got %v", res)
	}
	// install dir untouched, no backup taken
	got, _ := os.ReadFile(filepath.Join(installDir, "meshchatx-desktop"))
	if string(got) != "old-shell" {
		t.Fatal("install dir modified after rejected archive")
	}
	if _, err := os.Stat(installDir + ".bak"); !os.IsNotExist(err) {
		t.Fatal("backup dir created after rejected archive")
	}
	if _, err := os.Stat(filepath.Join(filepath.Dir(installDir), "escape.txt")); !os.IsNotExist(err) {
		t.Fatal("zip-slip file escaped extraction root")
	}
}

func TestApplyPendingOtherNonArchiveIsManual(t *testing.T) {
	dir := t.TempDir()
	installDir := makeInstallDir(t)
	t.Setenv("PORTABLE_EXECUTABLE_DIR", installDir)

	_, marker := stageFile(t, dir, "MeshChatX.bin", []byte("raw-bytes"))
	marker["kind"] = "other"
	writeMarker(t, dir, marker)

	res := ApplyPending(dir)
	if res["applied"] != false || res["mode"] != "manual" {
		t.Fatalf("res: %v", res)
	}
}
