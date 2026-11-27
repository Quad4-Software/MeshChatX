// Package updateapply ports electron/updateApply.js: apply a backend-staged
// update payload (updates/pending) to an AppImage install.
package updateapply

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var sha256HexRe = regexp.MustCompile(`(?i)^[0-9a-f]{64}$`)

func sha256File(filePath string) (string, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func ReadPendingMarker(storageDir string) map[string]any {
	data, err := os.ReadFile(filepath.Join(storageDir, "updates", "pending.json"))
	if err != nil {
		return nil
	}
	var marker map[string]any
	if err := json.Unmarshal(data, &marker); err != nil {
		return nil
	}
	return marker
}

// PendingApplyPolicy returns the apply_policy recorded in pending.json
// ("manual" or "on_restart"), or "" when absent.
func PendingApplyPolicy(storageDir string) string {
	marker := ReadPendingMarker(storageDir)
	if marker == nil {
		return ""
	}
	policy, _ := marker["apply_policy"].(string)
	return policy
}

func ClearPending(storageDir string) {
	_ = os.Remove(filepath.Join(storageDir, "updates", "pending.json"))
}

// ApplyPendingUpdate returns {applied:true} or {applied:false,error:...}.
func ApplyPendingUpdate(storageDir string) map[string]any {
	fail := func(err string, extra map[string]any) map[string]any {
		out := map[string]any{"applied": false, "error": err}
		for k, v := range extra {
			out[k] = v
		}
		return out
	}

	marker := ReadPendingMarker(storageDir)
	if marker == nil {
		return fail("no_pending_update", nil)
	}
	file, _ := marker["file"].(string)
	sha, _ := marker["sha256"].(string)
	kind, _ := marker["kind"].(string)
	if file == "" || filepath.Base(file) != file || !sha256HexRe.MatchString(sha) {
		return fail("bad_pending_marker", nil)
	}
	if kind != "appimage" {
		return fail("unsupported_kind", map[string]any{"kind": kind})
	}
	target := os.Getenv("APPIMAGE")
	if target == "" {
		return fail("not_appimage", nil)
	}
	pendingDir := filepath.Clean(filepath.Join(storageDir, "updates", "pending"))
	stagedPath := filepath.Join(pendingDir, file)
	if !strings.HasPrefix(stagedPath, pendingDir+string(filepath.Separator)) {
		return fail("path_escape", nil)
	}
	info, err := os.Stat(stagedPath)
	if err != nil || info.IsDir() {
		return fail("staged_missing", nil)
	}
	actual, err := sha256File(stagedPath)
	if err != nil || actual != strings.ToLower(sha) {
		return fail("sha256_mismatch", nil)
	}

	targetPath := filepath.Clean(target)
	if sameFile(stagedPath, targetPath) {
		return fail("same_path", nil)
	}

	backup := targetPath + ".bak"
	if _, err := os.Stat(targetPath); err == nil {
		if err := copyFileSync(targetPath, backup); err != nil {
			return fail(fmt.Sprintf("backup_failed: %s", err.Error()), nil)
		}
	}
	// Re-verify the staged bytes right before the swap; the earlier hash
	// check leaves a window where the file could be replaced.
	if again, err := sha256File(stagedPath); err != nil || again != strings.ToLower(sha) {
		return fail("sha256_mismatch", nil)
	}
	_ = os.Chmod(stagedPath, 0o755)
	if err := os.Rename(stagedPath, targetPath); err != nil {
		if cerr := replaceFileByCopy(stagedPath, targetPath, 0o755); cerr != nil {
			return fail(fmt.Sprintf("swap_failed: %s", cerr.Error()), nil)
		}
		_ = os.Remove(stagedPath)
	}
	fsyncFile(targetPath)
	fsyncDir(filepath.Dir(targetPath))
	ClearPending(storageDir)
	return map[string]any{"applied": true}
}

func sameFile(a, b string) bool {
	if filepath.Clean(a) == filepath.Clean(b) {
		return true
	}
	ra, errA := filepath.EvalSymlinks(a)
	rb, errB := filepath.EvalSymlinks(b)
	if errA == nil && errB == nil && ra == rb {
		return true
	}
	ai, errA := os.Stat(a)
	bi, errB := os.Stat(b)
	return errA == nil && errB == nil && os.SameFile(ai, bi)
}

func copyFileSync(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	info, err := in.Stat()
	if err != nil {
		return err
	}
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	written, err := io.Copy(out, in)
	if err == nil && written != info.Size() {
		err = fmt.Errorf("short copy: %d of %d bytes", written, info.Size())
	}
	if err == nil {
		err = out.Sync()
	}
	if cerr := out.Close(); err == nil {
		err = cerr
	}
	return err
}

func fsyncFile(path string) {
	if f, err := os.Open(path); err == nil {
		_ = f.Sync()
		_ = f.Close()
	}
}

func fsyncDir(dir string) {
	if f, err := os.Open(dir); err == nil {
		_ = f.Sync()
		_ = f.Close()
	}
}

// replaceFileByCopy swaps src into dst for cross-device cases where
// os.Rename fails: copy to a temp sibling of dst, then rename within the
// same directory so the final swap stays atomic.
func replaceFileByCopy(src, dst string, mode os.FileMode) error {
	dir := filepath.Dir(dst)
	tmp, err := os.CreateTemp(dir, ".swap-*")
	if err != nil {
		return err
	}
	tmpPath := tmp.Name()
	ok := false
	defer func() {
		if !ok {
			_ = os.Remove(tmpPath)
		}
	}()
	in, err := os.Open(src)
	if err != nil {
		tmp.Close()
		return err
	}
	if _, err := io.Copy(tmp, in); err != nil {
		in.Close()
		tmp.Close()
		return err
	}
	if err := in.Close(); err != nil {
		tmp.Close()
		return err
	}
	if err := os.Chmod(tmpPath, mode); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	if err := os.Rename(tmpPath, dst); err != nil {
		return err
	}
	ok = true
	return nil
}
