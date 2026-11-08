// Package integrity verifies backend files against backend-manifest.json,
// porting electron/backendIntegrity.js.
package integrity

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Result struct {
	OK     bool     `json:"ok"`
	Issues []string `json:"issues"`
}

// VerifyBackendIntegrity checks SHA-256 hashes of files listed in
// <exeDir>/backend-manifest.json. A missing manifest is ok-with-issue.
func VerifyBackendIntegrity(exeDir string) Result {
	manifestPath := filepath.Join(exeDir, "backend-manifest.json")
	if _, err := os.Stat(manifestPath); err != nil {
		return Result{OK: true, Issues: []string{"Manifest missing"}}
	}
	data, err := os.ReadFile(manifestPath)
	if err != nil {
		return Result{OK: false, Issues: []string{err.Error()}}
	}
	var manifest map[string]any
	if err := json.Unmarshal(data, &manifest); err != nil {
		return Result{OK: false, Issues: []string{err.Error()}}
	}

	filesToVerify := manifest
	var metadata map[string]any
	if f, ok := manifest["files"].(map[string]any); ok {
		filesToVerify = f
	}
	if m, ok := manifest["_metadata"].(map[string]any); ok {
		metadata = m
	}

	var issues []string
	for relPath, expectedRaw := range filesToVerify {
		expectedHash, ok := expectedRaw.(string)
		if !ok {
			continue
		}
		fullPath := filepath.Join(exeDir, relPath)
		content, err := os.ReadFile(fullPath)
		if err != nil {
			issues = append(issues, fmt.Sprintf("Missing: %s", relPath))
			continue
		}
		sum := sha256.Sum256(content)
		actualHash := hex.EncodeToString(sum[:])
		if actualHash != expectedHash {
			issues = append(issues, fmt.Sprintf("Modified: %s", relPath))
		}
	}

	if len(issues) > 0 && metadata != nil {
		if date, ok := metadata["date"].(string); ok {
			if tm, ok := metadata["time"].(string); ok {
				issues = append([]string{fmt.Sprintf("Backend build timestamp: %s %s", date, tm)}, issues...)
			}
		}
	}
	return Result{OK: len(issues) == 0, Issues: issues}
}
