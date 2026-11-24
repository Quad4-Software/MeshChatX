// Package updater applies backend-staged, signature-verified update
// artifacts for every install kind the update manifest can produce.
//
// The backend (meshchatx/src/backend/update_manager.py) downloads an
// artifact, verifies sha256+size against the signed manifest and stages it
// into <storage>/updates/pending/ with an atomic pending.json marker:
//
//	{"version":1, "staged_at":..., "channel":..., "apply_policy":"manual|on_restart",
//	 "file":name, "sha256":hex, "kind":kind, "platform":plat,
//	 "artifacts":[{"file","sha256","size","kind","platform","arch","version",...}]}
//
// This package re-verifies the staged bytes (sha256 always, size whenever
// the marker declares it) and then dispatches on kind:
//
//	appimage          -> swap+backup+relaunch (delegates to updateapply)
//	exe/msi/tarball   -> portable install-dir swap when the dir carries the
//	                     self-updatable marker (updatable.txt) and the
//	                     payload is an extractable archive; manual otherwise
//	other (archives)  -> same portable dir swap (the backend normalizes the
//	                     manifest "zip" kind to "other")
//	dmg/deb/rpm/...   -> manual instructions; the staged path is reported
//	oci/docker/flatpak-> external instructions; nothing is staged to apply
//
// Every result is a JSON-shaped map. Success is
// {"applied":true,"kind":k,"mode":"relaunch"}; manual/external reports are
// {"applied":false,"kind":k,"mode":"manual"|"external","reason":...,
// "path":...,"instructions":...}; hard failures keep the legacy
// {"applied":false,"error":code} shape.
package updater

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/updateapply"
)

var sha256HexRe = regexp.MustCompile(`(?i)^[0-9a-f]{64}$`)

// rolloutFlag gates the whole apply path until the staged update rollout
// is finalized. MESHCHATX_UPDATE_ROLLOUT=1 re-enables it for development
// and testing. Mirrors UPDATE_ROLLOUT_ENABLED in update_types.py.
const rolloutFlag = false

// RolloutEnabled reports whether staged updates may be applied.
func RolloutEnabled() bool {
	if rolloutFlag {
		return true
	}
	switch strings.ToLower(strings.TrimSpace(os.Getenv("MESHCHATX_UPDATE_ROLLOUT"))) {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}

// ReadPendingMarker returns the parsed pending.json marker, or nil when
// absent/unreadable/corrupt. Re-exported from updateapply so marker parsing
// stays single-sourced.
func ReadPendingMarker(storageDir string) map[string]any {
	return updateapply.ReadPendingMarker(storageDir)
}

// PendingApplyPolicy returns the apply_policy recorded in pending.json
// ("manual" or "on_restart"), or "" when absent.
func PendingApplyPolicy(storageDir string) string {
	return updateapply.PendingApplyPolicy(storageDir)
}

// ClearPending removes pending.json after a successful apply.
func ClearPending(storageDir string) {
	updateapply.ClearPending(storageDir)
}

func failResult(err, kind string, extra map[string]any) map[string]any {
	out := map[string]any{"applied": false, "error": err}
	if kind != "" {
		out["kind"] = kind
	}
	for k, v := range extra {
		out[k] = v
	}
	return out
}

func manualResult(kind, reason, stagedPath, instructions string) map[string]any {
	out := map[string]any{
		"applied": false,
		"kind":    kind,
		"mode":    "manual",
		"reason":  reason,
		"path":    stagedPath,
	}
	if instructions != "" {
		out["instructions"] = instructions
	}
	return out
}

func externalResult(kind, instructions string) map[string]any {
	return map[string]any{
		"applied":      false,
		"kind":         kind,
		"mode":         "external",
		"instructions": instructions,
	}
}

func appliedResult(kind string) map[string]any {
	return map[string]any{"applied": true, "kind": kind, "mode": "relaunch"}
}

// manualInstructions is the per-kind text reported when the shell cannot
// apply the staged artifact itself. Mirrors _apply_mode in
// meshchatx/src/backend/http/routes/update.py.
func manualInstructions(kind, file string) string {
	switch kind {
	case "exe", "msi":
		return fmt.Sprintf("Run the staged installer (%s) to finish the update.", file)
	case "dmg":
		return fmt.Sprintf("Open the staged DMG (%s) and drag MeshChatX into Applications to finish the update.", file)
	case "deb":
		return fmt.Sprintf("Install the staged package with your package manager, e.g. sudo apt install ./%s or sudo dpkg -i %s.", file, file)
	case "rpm":
		return fmt.Sprintf("Install the staged package with your package manager, e.g. sudo dnf install %s or sudo rpm -U %s.", file, file)
	case "wheel", "pyz":
		return fmt.Sprintf("Install the verified file with your package manager, e.g. uv pip install %s.", file)
	case "apk":
		return fmt.Sprintf("Open the staged APK (%s) to install; Android verifies the package signature.", file)
	default:
		return fmt.Sprintf("Install the staged file (%s) with your OS package manager.", file)
	}
}

// stagedArtifactPath resolves marker["file"] inside updates/pending and
// rejects any path escaping the pending dir.
func stagedArtifactPath(storageDir, file string) (string, bool) {
	pendingDir := filepath.Clean(filepath.Join(storageDir, "updates", "pending"))
	stagedPath := filepath.Join(pendingDir, file)
	if !strings.HasPrefix(stagedPath, pendingDir+string(filepath.Separator)) {
		return "", false
	}
	return stagedPath, true
}

// artifactEntry finds the marker's artifacts[] entry matching file.
func artifactEntry(marker map[string]any, file string) map[string]any {
	arts, _ := marker["artifacts"].([]any)
	for _, a := range arts {
		m, _ := a.(map[string]any)
		if m != nil {
			if f, _ := m["file"].(string); f == file {
				return m
			}
		}
	}
	return nil
}

func jsonSize(v any) (int64, bool) {
	switch n := v.(type) {
	case float64:
		return int64(n), n > 0
	case int64:
		return n, n > 0
	case int:
		return int64(n), n > 0
	}
	return 0, false
}

// verifyStaged re-checks the staged artifact against the marker before any
// swap runs (fail closed): basename/sha shape, pending-dir confinement,
// declared size when present, and the whole-file sha256.
func verifyStaged(storageDir string, marker map[string]any) (stagedPath, file, kind, sha string, errRes map[string]any) {
	file, _ = marker["file"].(string)
	sha, _ = marker["sha256"].(string)
	kind, _ = marker["kind"].(string)
	if file == "" || filepath.Base(file) != file || !sha256HexRe.MatchString(sha) {
		return "", "", kind, "", failResult("bad_pending_marker", kind, nil)
	}
	// Never swap in a payload built for another OS. "python" artifacts are
	// platform-agnostic; anything else must map to the host GOOS — unknown
	// platform strings fail closed.
	if plat, _ := marker["platform"].(string); plat != "" && plat != "python" {
		goos, known := map[string]string{
			"linux": "linux", "windows": "windows", "macos": "darwin", "android": "android",
		}[plat]
		if !known || goos != runtime.GOOS {
			return "", "", kind, "", failResult("platform_mismatch", kind, nil)
		}
	}
	var ok bool
	stagedPath, ok = stagedArtifactPath(storageDir, file)
	if !ok {
		return "", "", kind, "", failResult("path_escape", kind, nil)
	}
	info, err := os.Stat(stagedPath)
	if err != nil || info.IsDir() {
		return "", "", kind, "", failResult("staged_missing", kind, nil)
	}
	// Cross-check the artifacts[] entry the backend wrote: a mismatched
	// entry hash means the marker is corrupt/tampered.
	if entry := artifactEntry(marker, file); entry != nil {
		if esha, _ := entry["sha256"].(string); esha != "" && !strings.EqualFold(esha, sha) {
			return "", "", kind, "", failResult("bad_pending_marker", kind, nil)
		}
		if want, ok := jsonSize(entry["size"]); ok && want != info.Size() {
			return "", "", kind, "", failResult("size_mismatch", kind, nil)
		}
	} else if want, ok := jsonSize(marker["size"]); ok && want != info.Size() {
		return "", "", kind, "", failResult("size_mismatch", kind, nil)
	}
	actual, err := sha256File(stagedPath)
	if err != nil || actual != strings.ToLower(sha) {
		return "", "", kind, "", failResult("sha256_mismatch", kind, nil)
	}
	return stagedPath, file, kind, sha, nil
}

// ApplyPending applies the staged update described by pending.json.
//
// Returns {"applied":true,"kind":k,"mode":"relaunch"} when the artifact was
// swapped in and the caller should relaunch; {"applied":false,"kind":k,
// "mode":"manual"|"external",...} when the kind cannot self-apply (the
// staged path and instructions are reported, startup must not block on it);
// or {"applied":false,"error":code} on verification/IO failure. Nothing is
// touched when the marker is missing, incomplete, or fails verification.
func ApplyPending(storageDir string) map[string]any {
	if !RolloutEnabled() {
		return map[string]any{
			"applied": false,
			"error":   "rollout_disabled",
			"detail":  "staged update apply is disabled until the rollout is finalized",
		}
	}
	marker := ReadPendingMarker(storageDir)
	if marker == nil {
		return failResult("no_pending_update", "", nil)
	}
	stagedPath, file, kind, sha, errRes := verifyStaged(storageDir, marker)
	if errRes != nil {
		return errRes
	}

	switch kind {
	case "appimage":
		// AppImage swap+backup+relaunch lives in updateapply; delegate so
		// the proven implementation (and its tests) stay authoritative.
		res := updateapply.ApplyPendingUpdate(storageDir)
		res["kind"] = kind
		if res["applied"] == true {
			res["mode"] = "relaunch"
		}
		return res
	case "exe", "msi", "tarball":
		return applyPortable(storageDir, stagedPath, file, kind, sha)
	case "dmg", "deb", "rpm", "apk":
		return manualResult(kind, "package_managed_install", stagedPath, manualInstructions(kind, file))
	case "wheel", "pyz":
		return manualResult(kind, "python_package", stagedPath, manualInstructions(kind, file))
	case "oci", "docker":
		return externalResult(kind, "Pull the new image with your container runtime, e.g. docker pull <image>.")
	case "flatpak":
		return externalResult(kind, "Update the app with flatpak update.")
	default:
		// "other" and unknown kinds: the backend normalizes the manifest
		// "zip" kind to "other", so an archive payload on a self-updatable
		// install dir still gets the portable swap.
		if detectArchive(stagedPath) != "" {
			return applyPortable(storageDir, stagedPath, file, kind, sha)
		}
		return manualResult(kind, "manual_install", stagedPath, manualInstructions(kind, file))
	}
}
