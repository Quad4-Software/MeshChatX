// Portable install-dir swap for self-contained installs (portable zip /
// tarball layouts: the shell executable plus backend/ inside one directory
// the packaging marked as self-updatable).
//
// A directory is only treated as self-updatable when packaging wrote
// updatableMarkerName ("updatable.txt") into it; without that marker the
// staged artifact is always reported for manual install. The swap itself is
// backup -> extract -> rename, so the previous install stays at <dir>.bak.
package updater

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// updatableMarkerName is the opt-in marker packaging writes into portable
// install dirs that the shell may swap atomically.
const updatableMarkerName = "updatable.txt"

// installDirResolver resolves the directory that contains the running
// install. PORTABLE_EXECUTABLE_DIR (the portable-app convention) wins;
// otherwise the running executable's directory. A var so tests can stub it.
var installDirResolver = func() (string, error) {
	if d := strings.TrimSpace(os.Getenv("PORTABLE_EXECUTABLE_DIR")); d != "" {
		return filepath.Clean(d), nil
	}
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Dir(exe), nil
}

// osExecutable resolves the running executable path; a var so tests can stub
// it when exercising the PORTABLE_EXECUTABLE_DIR containment check.
var osExecutable = os.Executable

// selfUpdatableInstallDir returns the resolved install dir and whether it is
// a safe, self-updatable target: must exist, must not be a filesystem root
// or the user's home directory (a stray marker must never let us rename
// those), and must contain the packaging updatable marker.
func selfUpdatableInstallDir() (dir string, updatable bool, err error) {
	dir, err = installDirResolver()
	if err != nil {
		return "", false, err
	}
	if !filepath.IsAbs(dir) {
		dir, err = filepath.Abs(dir)
		if err != nil {
			return "", false, err
		}
	}
	dir = filepath.Clean(dir)
	parent := filepath.Dir(dir)
	if parent == dir {
		return dir, false, nil // filesystem root
	}
	if home, herr := os.UserHomeDir(); herr == nil && home != "" && filepath.Clean(home) == dir {
		return dir, false, nil // never swap a home dir
	}
	if st, serr := os.Stat(dir); serr != nil || !st.IsDir() {
		return dir, false, nil
	}
	// When PORTABLE_EXECUTABLE_DIR redirected the install dir, only honor it
	// if the running executable actually lives inside it; otherwise a stray
	// env var plus a planted marker could aim the swap at an arbitrary dir.
	if strings.TrimSpace(os.Getenv("PORTABLE_EXECUTABLE_DIR")) != "" {
		exe, eerr := osExecutable()
		if eerr != nil || !strings.HasPrefix(filepath.Clean(exe), dir+string(filepath.Separator)) {
			return dir, false, nil
		}
	}
	if st, serr := os.Stat(filepath.Join(dir, updatableMarkerName)); serr != nil || st.IsDir() {
		return dir, false, nil
	}
	return dir, true, nil
}

// detectArchive sniffs the staged payload. Returns "zip", "tar", "targz",
// "xz" (recognized but unsupported), or "" when the payload is not an
// archive we can extract.
func detectArchive(path string) string {
	f, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer f.Close()
	buf := make([]byte, 512)
	n, _ := f.Read(buf)
	buf = buf[:n]
	if len(buf) >= 4 && bytes.HasPrefix(buf, []byte{'P', 'K', 0x03, 0x04}) ||
		len(buf) >= 4 && bytes.HasPrefix(buf, []byte{'P', 'K', 0x05, 0x06}) ||
		len(buf) >= 4 && bytes.HasPrefix(buf, []byte{'P', 'K', 0x07, 0x08}) {
		return "zip"
	}
	if len(buf) >= 2 && buf[0] == 0x1f && buf[1] == 0x8b {
		return "targz"
	}
	if len(buf) >= 6 && bytes.HasPrefix(buf, []byte{0xfd, '7', 'z', 'X', 'Z', 0x00}) {
		return "xz"
	}
	if len(buf) > 262 && string(buf[257:262]) == "ustar" {
		return "tar"
	}
	lower := strings.ToLower(filepath.Base(path))
	switch {
	case strings.HasSuffix(lower, ".tar.xz"), strings.HasSuffix(lower, ".txz"):
		return "xz"
	case strings.HasSuffix(lower, ".tar.gz"), strings.HasSuffix(lower, ".tgz"):
		return "targz"
	case strings.HasSuffix(lower, ".tar"):
		return "tar"
	case strings.HasSuffix(lower, ".zip"):
		return "zip"
	}
	return ""
}

// applyPortable handles the exe/msi/tarball/other-archive kinds: a staged
// payload applied to a self-contained install dir the shell controls.
func applyPortable(storageDir, stagedPath, file, kind, sha string) map[string]any {
	installDir, updatable, err := selfUpdatableInstallDir()
	if err != nil || !updatable {
		reason := "not_self_updatable"
		if err != nil {
			reason = "install_dir_unresolvable"
		}
		return manualResult(kind, reason, stagedPath, manualInstructions(kind, file))
	}
	// Never swap a directory that contains the staged file itself.
	if strings.HasPrefix(stagedPath, installDir+string(filepath.Separator)) {
		return manualResult(kind, "not_self_updatable", stagedPath, manualInstructions(kind, file))
	}
	arch := detectArchive(stagedPath)
	if arch == "" || arch == "xz" {
		// NSIS/MSI installers and xz payloads can't be extracted in
		// process; the user runs the staged file.
		return manualResult(kind, "payload_not_extractable", stagedPath, manualInstructions(kind, file))
	}
	// Re-verify the staged bytes immediately before the swap: the marker
	// hash was checked earlier and the file could have been replaced since.
	if actual, herr := sha256File(stagedPath); herr != nil || actual != strings.ToLower(sha) {
		return failResult("sha256_mismatch", kind, nil)
	}
	if err := extractAndSwap(installDir, stagedPath, arch); err != nil {
		return failResult(err.Error(), kind, nil)
	}
	// The payload replaced the install; the staged archive is consumed.
	_ = os.Remove(stagedPath)
	ClearPending(storageDir)
	return appliedResult(kind)
}

// extractAndSwap extracts the staged archive next to the install dir, then
// atomically renames install -> .bak and payload -> install. On a mid-swap
// failure it tries to restore the backup before reporting the error.
func extractAndSwap(installDir, stagedPath, arch string) error {
	parent := filepath.Dir(installDir)
	staging := installDir + ".new"
	bak := installDir + ".bak"

	if err := os.RemoveAll(staging); err != nil {
		return fmt.Errorf("extract_failed: %s", err.Error())
	}
	if err := os.MkdirAll(staging, 0o755); err != nil {
		return fmt.Errorf("extract_failed: %s", err.Error())
	}
	extracted := false
	defer func() {
		if !extracted {
			_ = os.RemoveAll(staging)
		}
	}()
	if err := extractArchive(stagedPath, staging, arch); err != nil {
		return fmt.Errorf("extract_failed: %s", err.Error())
	}
	// Archives usually wrap the payload in a single root directory
	// (e.g. meshchatx-desktop-portable/); unwrap exactly one such level.
	payload := staging
	if entries, err := os.ReadDir(staging); err == nil {
		if len(entries) == 1 && entries[0].IsDir() {
			payload = filepath.Join(staging, entries[0].Name())
		}
	}
	entries, err := os.ReadDir(payload)
	if err != nil {
		return fmt.Errorf("extract_failed: %s", err.Error())
	}
	if len(entries) == 0 {
		return fmt.Errorf("extract_failed: empty payload")
	}

	// The marker attests this install location is a self-contained dir the
	// shell may swap; carry it forward when the new payload omits it so the
	// property survives the update. Done before the swap so a failure here
	// still leaves the running install untouched.
	if _, err := os.Stat(filepath.Join(payload, updatableMarkerName)); err != nil {
		if err := copyFileSync(
			filepath.Join(installDir, updatableMarkerName),
			filepath.Join(payload, updatableMarkerName),
		); err != nil {
			return fmt.Errorf("extract_failed: %s", err.Error())
		}
	}
	extracted = true

	if err := os.RemoveAll(bak); err != nil {
		return fmt.Errorf("backup_failed: %s", err.Error())
	}
	if err := os.Rename(installDir, bak); err != nil {
		return fmt.Errorf("backup_failed: %s", err.Error())
	}
	if err := os.Rename(payload, installDir); err != nil {
		// Restore the backup so the install is not left missing.
		_ = os.Rename(bak, installDir)
		_ = os.RemoveAll(staging)
		return fmt.Errorf("swap_failed: %s", err.Error())
	}
	_ = os.RemoveAll(staging) // leftover wrapper dir when payload was nested

	fsyncDir(installDir)
	fsyncDir(parent)
	return nil
}
