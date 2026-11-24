// Package settings persists the small JSON preference files the Electron
// shell kept in the storage dir: close behavior, UI theme, screen security.
package settings

import (
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/fsutil"
)

// ---- close behavior (electron/closeBehavior.js) ---------------------------

var closeBehaviors = map[string]bool{"ask": true, "quit": true, "background": true}

type CloseSettings struct {
	CloseBehavior string `json:"closeBehavior"`
	TrayEnabled   bool   `json:"trayEnabled"`
}

func DefaultCloseSettings() CloseSettings {
	return CloseSettings{CloseBehavior: "ask", TrayEnabled: true}
}

func CloseSettingsPath(storageDir string) string {
	return filepath.Join(storageDir, "desktop-close-settings.json")
}

func NormalizeCloseSettings(raw map[string]any) CloseSettings {
	def := DefaultCloseSettings()
	if raw == nil {
		return def
	}
	out := def
	if v, ok := raw["closeBehavior"].(string); ok && closeBehaviors[v] {
		out.CloseBehavior = v
	}
	if v, ok := raw["trayEnabled"].(bool); ok {
		out.TrayEnabled = v
	}
	return out
}

func LoadCloseSettings(storageDir string) CloseSettings {
	data, err := os.ReadFile(CloseSettingsPath(storageDir))
	if err != nil {
		return DefaultCloseSettings()
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return DefaultCloseSettings()
	}
	return NormalizeCloseSettings(raw)
}

func SaveCloseSettings(storageDir string, partial map[string]any) CloseSettings {
	current := LoadCloseSettings(storageDir)
	merged := map[string]any{
		"closeBehavior": current.CloseBehavior,
		"trayEnabled":   current.TrayEnabled,
	}
	for k, v := range partial {
		merged[k] = v
	}
	next := NormalizeCloseSettings(merged)
	writeJSON(CloseSettingsPath(storageDir), next)
	return next
}

// ResolveCloseAction maps settings to "ask"|"quit"|"background"|"minimize".
func ResolveCloseAction(s CloseSettings) string {
	s = NormalizeCloseSettings(map[string]any{"closeBehavior": s.CloseBehavior, "trayEnabled": s.TrayEnabled})
	switch s.CloseBehavior {
	case "ask":
		return "ask"
	case "quit":
		return "quit"
	}
	if !s.TrayEnabled {
		return "minimize"
	}
	return "background"
}

// RememberedCloseSettings maps a chosen action + remember flag into persisted
// settings, or nil when nothing should be persisted.
func RememberedCloseSettings(action string, remember bool) map[string]any {
	if !remember {
		return nil
	}
	switch action {
	case "quit":
		return map[string]any{"closeBehavior": "quit"}
	case "background", "minimize":
		return map[string]any{"closeBehavior": "background"}
	}
	return nil
}

// CloseRequestGuard blocks re-entrant close handling. Window-closing hooks
// can fire on multiple goroutines, so the flag must be atomic.
type CloseRequestGuard struct {
	inFlight atomic.Bool
}

func (g *CloseRequestGuard) TryEnter() bool {
	return g.inFlight.CompareAndSwap(false, true)
}

func (g *CloseRequestGuard) Leave() { g.inFlight.Store(false) }

// ---- UI theme (electron/uiTheme.js) ---------------------------------------

var uiThemes = map[string]bool{"light": true, "dark": true, "system": true}

func UiThemePath(storageDir string) string {
	return filepath.Join(storageDir, "desktop-ui-theme.json")
}

func NormalizeUiThemePreference(raw any) string {
	s, ok := raw.(string)
	if !ok {
		return "system"
	}
	v := strings.ToLower(strings.TrimSpace(s))
	if uiThemes[v] {
		return v
	}
	return "system"
}

func ResolveEffectiveUiTheme(preference string, prefersDark bool) string {
	switch NormalizeUiThemePreference(preference) {
	case "light", "dark":
		return NormalizeUiThemePreference(preference)
	}
	if prefersDark {
		return "dark"
	}
	return "light"
}

func LoadUiThemePreference(storageDir string) string {
	data, err := os.ReadFile(UiThemePath(storageDir))
	if err != nil {
		return "system"
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return "system"
	}
	if v, ok := raw["preference"].(string); ok {
		return NormalizeUiThemePreference(v)
	}
	if v, ok := raw["theme"].(string); ok {
		return NormalizeUiThemePreference(v)
	}
	return "system"
}

func SaveUiThemePreference(storageDir string, preference string) string {
	next := NormalizeUiThemePreference(preference)
	writeJSON(UiThemePath(storageDir), map[string]any{"preference": next})
	return next
}

func ShellBackgroundColor(effectiveTheme string) string {
	if effectiveTheme == "dark" {
		return "#09090b"
	}
	return "#f8fafc"
}

// ---- desktop privacy settings (electron/desktopPrivacySettings.js) --------

type DesktopPrivacySettings struct {
	ScreenSecurityEnabled bool `json:"screenSecurityEnabled"`
}

func DefaultDesktopPrivacySettings() DesktopPrivacySettings {
	return DesktopPrivacySettings{ScreenSecurityEnabled: false}
}

func DesktopPrivacySettingsPath(storageDir string) string {
	return filepath.Join(storageDir, "desktop-privacy-settings.json")
}

func NormalizeDesktopPrivacySettings(raw map[string]any) DesktopPrivacySettings {
	def := DefaultDesktopPrivacySettings()
	if raw == nil {
		return def
	}
	out := def
	if v, ok := raw["screenSecurityEnabled"].(bool); ok {
		out.ScreenSecurityEnabled = v
	}
	return out
}

func LoadDesktopPrivacySettings(storageDir string) DesktopPrivacySettings {
	data, err := os.ReadFile(DesktopPrivacySettingsPath(storageDir))
	if err != nil {
		return DefaultDesktopPrivacySettings()
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return DefaultDesktopPrivacySettings()
	}
	return NormalizeDesktopPrivacySettings(raw)
}

func SaveDesktopPrivacySettings(storageDir string, partial map[string]any) DesktopPrivacySettings {
	current := LoadDesktopPrivacySettings(storageDir)
	merged := map[string]any{"screenSecurityEnabled": current.ScreenSecurityEnabled}
	for k, v := range partial {
		merged[k] = v
	}
	next := NormalizeDesktopPrivacySettings(merged)
	writeJSON(DesktopPrivacySettingsPath(storageDir), next)
	return next
}

// IsScreenSecurityPlatformSupported: Windows is the primary target, macOS is
// also supported. Linux has no equivalent hook.
func IsScreenSecurityPlatformSupported(platform string) bool {
	return platform == "windows" || platform == "darwin"
}

// ---- window zoom -------------------------------------------------------------

const (
	windowZoomMin     = 0.5
	windowZoomMax     = 3.0
	windowZoomDefault = 1.0
	windowZoomStep    = 0.1
)

func WindowZoomPath(storageDir string) string {
	return filepath.Join(storageDir, "desktop-window-zoom.json")
}

func clampWindowZoom(level float64) float64 {
	if level < windowZoomMin {
		return windowZoomMin
	}
	if level > windowZoomMax {
		return windowZoomMax
	}
	return level
}

func NormalizeWindowZoom(raw any) float64 {
	f, ok := raw.(float64)
	if !ok || math.IsNaN(f) || math.IsInf(f, 0) {
		return windowZoomDefault
	}
	return clampWindowZoom(f)
}

func LoadWindowZoom(storageDir string) float64 {
	data, err := os.ReadFile(WindowZoomPath(storageDir))
	if err != nil {
		return windowZoomDefault
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return windowZoomDefault
	}
	return NormalizeWindowZoom(raw["zoom"])
}

func SaveWindowZoom(storageDir string, level float64) float64 {
	next := math.Round(clampWindowZoom(level)*10) / 10
	writeJSON(WindowZoomPath(storageDir), map[string]any{"zoom": next})
	return next
}

func WindowZoomStep(current float64, action string) float64 {
	var next float64
	switch action {
	case "in":
		next = current + windowZoomStep
	case "out":
		next = current - windowZoomStep
	case "reset":
		next = windowZoomDefault
	default:
		next = current
	}
	return math.Round(clampWindowZoom(next)*10) / 10
}

func writeJSON(path string, v any) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return
	}
	_ = fsutil.WriteFileAtomic(path, append(data, '\n'), 0o644)
}
