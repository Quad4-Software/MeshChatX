package mgrs

import (
	"os"
	"os/exec"
	"testing"
)

func requireTool(t *testing.T, name string) string {
	t.Helper()
	path, err := exec.LookPath(name)
	if err != nil {
		if os.Getenv("MGRS_REQUIRE_DIFF") != "" {
			t.Fatalf("%s required for differential checks but not found on PATH", name)
		}
		t.Skipf("%s not on PATH", name)
	}
	return path
}
