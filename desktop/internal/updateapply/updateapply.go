// Package updateapply ports electron/updateApply.js: apply a backend-staged
// update payload (updates/pending) to an AppImage install.
package updateapply

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
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
	buf := make([]byte, 1<<20)
	for {
		n, err := f.Read(buf)
		if n > 0 {
			h.Write(buf[:n])
		}
		if err != nil {
			break
		}
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
	if stagedPath == targetPath {
		return fail("same_path", nil)
	}

	backup := targetPath + ".bak"
	if in, err := os.Open(targetPath); err == nil {
		if out, err := os.Create(backup); err == nil {
			buf := make([]byte, 1<<20)
			for {
				n, rerr := in.Read(buf)
				if n > 0 {
					out.Write(buf[:n])
				}
				if rerr != nil {
					break
				}
			}
			out.Close()
		}
		in.Close()
	}
	_ = os.Chmod(stagedPath, 0o755)
	if err := os.Rename(stagedPath, targetPath); err != nil {
		return fail(fmt.Sprintf("swap_failed: %s", err.Error()), nil)
	}
	ClearPending(storageDir)
	return map[string]any{"applied": true}
}
