package integrity

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func sha(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func TestVerifyBackendIntegrity(t *testing.T) {
	// missing manifest -> ok with issue
	dir := t.TempDir()
	res := VerifyBackendIntegrity(dir)
	if !res.OK || len(res.Issues) != 1 || res.Issues[0] != "Manifest missing" {
		t.Fatalf("missing manifest: %+v", res)
	}

	// valid manifest
	if err := os.WriteFile(filepath.Join(dir, "app.bin"), []byte("hello"), 0o644); err != nil {
		t.Fatal(err)
	}
	manifest := map[string]any{
		"files": map[string]any{"app.bin": sha("hello")},
		"_metadata": map[string]any{
			"date": "2024-01-01", "time": "00:00:00",
		},
	}
	data, _ := json.Marshal(manifest)
	if err := os.WriteFile(filepath.Join(dir, "backend-manifest.json"), data, 0o644); err != nil {
		t.Fatal(err)
	}
	res = VerifyBackendIntegrity(dir)
	if !res.OK || len(res.Issues) != 0 {
		t.Fatalf("valid manifest: %+v", res)
	}

	// tampered file
	if err := os.WriteFile(filepath.Join(dir, "app.bin"), []byte("tampered"), 0o644); err != nil {
		t.Fatal(err)
	}
	res = VerifyBackendIntegrity(dir)
	if res.OK {
		t.Fatal("tampered file reported ok")
	}
	found := false
	for _, issue := range res.Issues {
		if strings.Contains(issue, "Modified: app.bin") {
			found = true
		}
		if strings.Contains(issue, "2024-01-01") {
			// timestamp prepended
		}
	}
	if !found {
		t.Fatalf("missing modified issue: %v", res.Issues)
	}

	// missing listed file
	manifest["files"] = map[string]any{"gone.bin": sha("x")}
	data, _ = json.Marshal(manifest)
	_ = os.WriteFile(filepath.Join(dir, "backend-manifest.json"), data, 0o644)
	res = VerifyBackendIntegrity(dir)
	if res.OK {
		t.Fatal("missing file reported ok")
	}
	found = false
	for _, issue := range res.Issues {
		if strings.Contains(issue, "Missing: gone.bin") {
			found = true
		}
	}
	if !found {
		t.Fatalf("missing issue: %v", res.Issues)
	}

	// corrupt manifest json
	_ = os.WriteFile(filepath.Join(dir, "backend-manifest.json"), []byte("{nope"), 0o644)
	res = VerifyBackendIntegrity(dir)
	if res.OK {
		t.Fatal("corrupt manifest reported ok")
	}
}
