package system

import (
	"os"
	"runtime"
	"testing"
)

func TestBackendMemoryEnvDefaults(t *testing.T) {
	if runtime.GOOS == "windows" {
		// glibc vars are still set (harmless); no OS gate in BackendMemoryEnv.
	}
	env := BackendMemoryEnv([]string{"PATH=/bin"})
	if env["MALLOC_ARENA_MAX"] != "2" || env["MALLOC_TRIM_THRESHOLD_"] != "131072" {
		t.Fatalf("defaults missing: %v", env)
	}
}

func TestBackendMemoryEnvUserWins(t *testing.T) {
	env := BackendMemoryEnv([]string{"MALLOC_ARENA_MAX=8", "OTHER=1"})
	if _, ok := env["MALLOC_ARENA_MAX"]; ok {
		t.Fatal("user-set MALLOC_ARENA_MAX was overridden")
	}
	if env["MALLOC_TRIM_THRESHOLD_"] != "131072" {
		t.Fatalf("unset var not defaulted: %v", env)
	}
}

func TestBackendMemoryEnvOptOut(t *testing.T) {
	t.Setenv("MESHCHATX_NO_MEM_TUNING", "1")
	if env := BackendMemoryEnv([]string{}); env != nil {
		t.Fatalf("opt-out still returned env: %v", env)
	}
}

func TestApplyMemoryTuningEnv(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("linux-only")
	}
	t.Setenv("MESHCHATX_NO_MEM_TUNING", "")
	t.Setenv("GSK_RENDERER", "")
	old := hasRenderNode
	defer func() { hasRenderNode = old }()

	hasRenderNode = func() bool { return false }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "cairo" {
		t.Fatalf("software GL: GSK_RENDERER=%q", os.Getenv("GSK_RENDERER"))
	}

	// GPU present -> no override.
	t.Setenv("GSK_RENDERER", "")
	hasRenderNode = func() bool { return true }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "" {
		t.Fatalf("GPU system: GSK_RENDERER=%q", os.Getenv("GSK_RENDERER"))
	}

	// User-set GSK_RENDERER wins.
	t.Setenv("GSK_RENDERER", "gl")
	hasRenderNode = func() bool { return false }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "gl" {
		t.Fatalf("user GSK_RENDERER overwritten: %q", os.Getenv("GSK_RENDERER"))
	}

	// Opt-out.
	t.Setenv("MESHCHATX_NO_MEM_TUNING", "1")
	t.Setenv("GSK_RENDERER", "")
	hasRenderNode = func() bool { return false }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "" {
		t.Fatalf("opt-out: GSK_RENDERER=%q", os.Getenv("GSK_RENDERER"))
	}
}
