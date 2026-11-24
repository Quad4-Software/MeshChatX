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
	t.Setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "")
	t.Setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "")
	old := hasRenderNode
	defer func() { hasRenderNode = old }()

	hasRenderNode = func() bool { return false }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "cairo" {
		t.Fatalf("software GL: GSK_RENDERER=%q", os.Getenv("GSK_RENDERER"))
	}
	if os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE") != "1" ||
		os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER") != "1" {
		t.Fatalf("software GL: webkit disables not set: %q %q",
			os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE"),
			os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER"))
	}

	// GPU present -> no override.
	t.Setenv("GSK_RENDERER", "")
	t.Setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "")
	t.Setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "")
	hasRenderNode = func() bool { return true }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "" ||
		os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE") != "" ||
		os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER") != "" {
		t.Fatalf("GPU system: env touched: %q %q %q",
			os.Getenv("GSK_RENDERER"),
			os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE"),
			os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER"))
	}

	// User-set values win, including "0"; unset vars still defaulted.
	t.Setenv("GSK_RENDERER", "gl")
	t.Setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "0")
	t.Setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "")
	hasRenderNode = func() bool { return false }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "gl" ||
		os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE") != "0" ||
		os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER") != "1" {
		t.Fatalf("user values not preserved per var: %q %q %q",
			os.Getenv("GSK_RENDERER"),
			os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE"),
			os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER"))
	}

	// Opt-out.
	t.Setenv("MESHCHATX_NO_MEM_TUNING", "1")
	t.Setenv("GSK_RENDERER", "")
	t.Setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "")
	t.Setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "")
	hasRenderNode = func() bool { return false }
	ApplyMemoryTuningEnv(nil)
	if os.Getenv("GSK_RENDERER") != "" ||
		os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE") != "" ||
		os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER") != "" {
		t.Fatalf("opt-out: env touched: %q %q %q",
			os.Getenv("GSK_RENDERER"),
			os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE"),
			os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER"))
	}
}
