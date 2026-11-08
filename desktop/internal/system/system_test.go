package system

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestLinuxBatteryLevelFrom(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("linux-only")
	}
	// empty dir -> not ok
	if _, ok := linuxBatteryLevelFrom(t.TempDir()); ok {
		t.Fatal("empty dir should not report level")
	}

	dir := t.TempDir()
	// BAT0 with valid capacity
	bat := filepath.Join(dir, "BAT0")
	if err := os.MkdirAll(bat, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(bat, "capacity"), []byte(" 87\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	// non-battery dirs ignored
	adp := filepath.Join(dir, "ADP1")
	_ = os.MkdirAll(adp, 0o755)
	_ = os.WriteFile(filepath.Join(adp, "capacity"), []byte("5"), 0o644)

	lvl, ok := linuxBatteryLevelFrom(dir)
	if !ok || lvl != 87 {
		t.Fatalf("level %d ok %v", lvl, ok)
	}

	// invalid capacity skipped
	if err := os.WriteFile(filepath.Join(bat, "capacity"), []byte("abc"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, ok := linuxBatteryLevelFrom(dir); ok {
		t.Fatal("invalid capacity should not report")
	}
	// out-of-range capacity skipped
	_ = os.WriteFile(filepath.Join(bat, "capacity"), []byte("250"), 0o644)
	if _, ok := linuxBatteryLevelFrom(dir); ok {
		t.Fatal("out-of-range capacity should not report")
	}
}

func TestGetMemoryUsage(t *testing.T) {
	m := GetMemoryUsage()
	if m.ResidentSet <= 0 {
		t.Fatalf("resident set should be positive: %+v", m)
	}
	if m.Private <= 0 {
		t.Fatalf("private should be positive: %+v", m)
	}
}

func TestHardwareAccelerationDisabled(t *testing.T) {
	dir := t.TempDir()
	argv := []string{"app"}
	if HardwareAccelerationDisabled(dir, argv) {
		t.Fatal("should be enabled by default")
	}
	if err := os.WriteFile(filepath.Join(dir, "disable-gpu"), []byte(""), 0o644); err != nil {
		t.Fatal(err)
	}
	if !HardwareAccelerationDisabled(dir, argv) {
		t.Fatal("disable-gpu file not honored")
	}
	os.Remove(filepath.Join(dir, "disable-gpu"))
	if !HardwareAccelerationDisabled(dir, []string{"app", "--disable-gpu"}) {
		t.Fatal("--disable-gpu arg not honored")
	}
	if !HardwareAccelerationDisabled(dir, []string{"app", "--disable-software-rasterizer"}) {
		t.Fatal("--disable-software-rasterizer not honored")
	}
	if HardwareAccelerationDisabled(dir, []string{"app", "--disable-gpu-sandbox"}) {
		t.Fatal("unrelated flag matched")
	}
}

func TestScreenSecurityPayload(t *testing.T) {
	w := ScreenSecurityPayload("windows", true)
	if !w.Available || !w.WindowsDrm || !w.Enabled || w.Platform != "windows" {
		t.Fatalf("windows payload: %+v", w)
	}
	d := ScreenSecurityPayload("darwin", false)
	if !d.Available || d.WindowsDrm || d.Enabled {
		t.Fatalf("darwin payload: %+v", d)
	}
	l := ScreenSecurityPayload("linux", true)
	if l.Available {
		t.Fatalf("linux should be unavailable: %+v", l)
	}
}

func TestApplyWebKitGpuEnv(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("linux-only")
	}
	os.Unsetenv("WEBKIT_DISABLE_COMPOSITING_MODE")
	os.Unsetenv("WEBKIT_DISABLE_DMABUF_RENDERER")
	ApplyWebKitGpuEnv(false)
	if os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE") == "1" {
		t.Fatal("env set when not disabled")
	}
	ApplyWebKitGpuEnv(true)
	if os.Getenv("WEBKIT_DISABLE_COMPOSITING_MODE") != "1" ||
		os.Getenv("WEBKIT_DISABLE_DMABUF_RENDERER") != "1" {
		t.Fatal("env not set when disabled")
	}
	os.Unsetenv("WEBKIT_DISABLE_COMPOSITING_MODE")
	os.Unsetenv("WEBKIT_DISABLE_DMABUF_RENDERER")
}

func TestBatteryStatusShape(t *testing.T) {
	// GetBatteryStatus may return nil on machines without batteries; when it
	// returns a value the shape must match the Electron contract.
	b := GetBatteryStatus()
	if b == nil {
		return
	}
	if b.Source != "wails" {
		t.Fatalf("source: %q", b.Source)
	}
	if b.Level != nil && (*b.Level < 0 || *b.Level > 100) {
		t.Fatalf("level out of range: %d", *b.Level)
	}
	// charging derived from onBattery
	if b.OnBattery != nil && b.Charging != nil && *b.Charging == *b.OnBattery {
		t.Fatalf("charging should be inverse of onBattery: %+v", b)
	}
	_ = strings.TrimSpace // keep strings import if unused elsewhere
}
