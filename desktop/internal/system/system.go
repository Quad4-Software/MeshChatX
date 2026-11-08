// Package system implements the OS-level shell services the Electron main
// process provided: battery status, memory usage, power-save blocker and
// screen security (content protection).
package system

import (
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
)

// ---- battery status --------------------------------------------------------

type BatteryStatus struct {
	Level     *int   `json:"level"`
	Charging  *bool  `json:"charging"`
	OnBattery *bool  `json:"on_battery"`
	Source    string `json:"source"`
}

// GetBatteryStatus mirrors the Electron handler: sysfs capacity on Linux,
// platform helpers elsewhere. Returns nil when nothing is known.
func GetBatteryStatus() *BatteryStatus {
	var onBattery *bool
	// Platform-specific power state (Linux: /sys/class/power_supply type).
	if b, ok := onBatteryPower(); ok {
		onBattery = &b
	}

	var level *int
	if runtime.GOOS == "linux" {
		if l, ok := linuxBatteryLevelFrom("/sys/class/power_supply"); ok {
			level = &l
		}
	}

	if level == nil && onBattery == nil {
		return nil
	}
	out := &BatteryStatus{Level: level, Source: "wails"}
	if onBattery != nil {
		out.OnBattery = onBattery
		charging := !*onBattery
		out.Charging = &charging
	}
	return out
}

func linuxBatteryLevelFrom(dir string) (int, bool) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0, false
	}
	for _, e := range entries {
		name := e.Name()
		upper := strings.ToUpper(name)
		isBat := false
		if len(upper) >= 3 && upper[:3] == "BAT" {
			rest := upper[3:]
			allDigits := rest != ""
			for _, c := range rest {
				if c < '0' || c > '9' {
					allDigits = false
					break
				}
			}
			isBat = allDigits
		}
		if !isBat && upper != "BATTERY" {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, name, "capacity"))
		if err != nil {
			continue
		}
		v, err := strconv.Atoi(strings.TrimSpace(string(data)))
		if err == nil && v >= 0 && v <= 100 {
			return v, true
		}
	}
	return 0, false
}

// ---- memory usage ----------------------------------------------------------

// MemoryUsage mirrors Electron's process.getProcessMemoryInfo shape (KB).
type MemoryUsage struct {
	Private        int64 `json:"private"`
	ResidentSet    int64 `json:"residentSet"`
	Shared         int64 `json:"shared"`
	WorkingSetSize int64 `json:"workingSetSize,omitempty"`
}

// GetMemoryUsage returns process memory in KB.
func GetMemoryUsage() MemoryUsage {
	if runtime.GOOS == "linux" {
		if m, ok := linuxMemoryUsage(); ok {
			return m
		}
	}
	return fallbackMemoryUsage()
}

func linuxMemoryUsage() (MemoryUsage, bool) {
	data, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return MemoryUsage{}, false
	}
	var rss, private, shared int64
	for _, line := range strings.Split(string(data), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		kb, err := strconv.ParseInt(fields[1], 10, 64)
		if err != nil {
			continue
		}
		switch fields[0] {
		case "VmRSS:":
			rss = kb
		case "RssAnon:":
			private = kb
		case "RssFile:", "RssShmem":
			shared += kb
		}
	}
	if rss == 0 {
		return MemoryUsage{}, false
	}
	if private == 0 {
		private = rss
	}
	return MemoryUsage{Private: private, ResidentSet: rss, Shared: shared}, true
}

func fallbackMemoryUsage() MemoryUsage {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	// Go heap is not the process RSS; report heap stats as a degraded fallback.
	return MemoryUsage{
		Private:     int64(ms.Alloc),
		ResidentSet: int64(ms.Sys),
		Shared:      0,
	}
}

// ---- hardware acceleration flag --------------------------------------------

// HardwareAccelerationDisabled reports whether the disable-gpu marker exists
// in the storage dir or disabling flags were passed on the command line.
func HardwareAccelerationDisabled(storageDir string, argv []string) bool {
	if _, err := os.Stat(filepath.Join(storageDir, "disable-gpu")); err == nil {
		return true
	}
	for _, arg := range argv {
		if arg == "--disable-gpu" || arg == "--disable-software-rasterizer" {
			return true
		}
	}
	return false
}

// ApplyWebKitGpuEnv sets the WebKitGTK env vars that mirror
// app.disableHardwareAcceleration() when GPU is disabled. Call before app.Run.
func ApplyWebKitGpuEnv(disabled bool) {
	if !disabled || runtime.GOOS != "linux" {
		return
	}
	os.Setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "1")
	os.Setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "1")
}

// ---- memory tuning ---------------------------------------------------------

// memTuningDisabled reports the MESHCHATX_NO_MEM_TUNING opt-out shared by
// all shell memory tuning (GSK renderer + backend malloc env).
func memTuningDisabled() bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv("MESHCHATX_NO_MEM_TUNING")))
	return v == "1" || v == "true" || v == "yes" || v == "on"
}

// hasRenderNode reports whether a /dev/dri/renderD* device exists (real GPU
// or virtio-gpu). Injectable for tests.
var hasRenderNode = func() bool {
	matches, err := filepath.Glob("/dev/dri/renderD*")
	return err == nil && len(matches) > 0
}

// ApplyMemoryTuningEnv applies Linux-only memory reducers before WebKit/GTK
// init. With no render node (software GL, e.g. llvmpipe) the GTK4 GL
// renderer is very heavy, so fall back to the much lighter cairo renderer —
// but only when the user has not chosen GSK_RENDERER themselves.
func ApplyMemoryTuningEnv(argv []string) {
	if runtime.GOOS != "linux" || memTuningDisabled() {
		return
	}
	if os.Getenv("GSK_RENDERER") == "" && !hasRenderNode() {
		os.Setenv("GSK_RENDERER", "cairo")
	}
}

// BackendMemoryEnv returns env overrides for the spawned backend child:
// glibc malloc arena/trim tuning that reduces the Python process's PSS.
// User-set values always win; returns nil when tuning is disabled or the
// vars are already present in the parent environment.
func BackendMemoryEnv(environ []string) map[string]string {
	if memTuningDisabled() {
		return nil
	}
	want := map[string]string{
		"MALLOC_ARENA_MAX":       "2",
		"MALLOC_TRIM_THRESHOLD_": "131072",
	}
	out := map[string]string{}
	for k, v := range want {
		found := false
		for _, kv := range environ {
			if strings.HasPrefix(kv, k+"=") {
				found = true
				break
			}
		}
		if !found {
			out[k] = v
		}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

// ---- power save blocker -----------------------------------------------------

// PowerSaveBlocker prevents the session idling while active.
type PowerSaveBlocker interface {
	Start() bool
	Stop() bool
	Active() bool
}

// NewPowerSaveBlocker is defined per-platform (power_<os>.go).

// ScreenSecurity reports the content-protection state per platform.
type ScreenSecurity struct {
	Platform   string `json:"platform"`
	Available  bool   `json:"available"`
	WindowsDrm bool   `json:"windowsDrm"`
	Enabled    bool   `json:"enabled"`
}

// Payload mirrors getScreenSecuritySettingsPayload().
func ScreenSecurityPayload(platform string, enabled bool) ScreenSecurity {
	return ScreenSecurity{
		Platform:   platform,
		Available:  platform == "windows" || platform == "darwin",
		WindowsDrm: platform == "windows",
		Enabled:    enabled,
	}
}
