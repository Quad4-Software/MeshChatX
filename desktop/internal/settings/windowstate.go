package settings

import (
	"encoding/json"
	"math"
	"os"
	"path/filepath"
)

// WindowState is the persisted main-window geometry.
type WindowState struct {
	Width     int  `json:"width"`
	Height    int  `json:"height"`
	X         int  `json:"x"`
	Y         int  `json:"y"`
	Maximized bool `json:"maximized"`
}

// ScreenRect is the subset of display geometry the validator needs, kept
// Wails-free so the logic stays unit-testable.
type ScreenRect struct {
	X      int
	Y      int
	Width  int
	Height int
}

func WindowStatePath(storageDir string) string {
	return filepath.Join(storageDir, "desktop-window-state.json")
}

func LoadWindowState(storageDir string) (WindowState, bool) {
	data, err := os.ReadFile(WindowStatePath(storageDir))
	if err != nil {
		return WindowState{}, false
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return WindowState{}, false
	}
	num := func(key string) (int, bool) {
		v, ok := raw[key].(float64)
		if !ok || math.IsNaN(v) || math.IsInf(v, 0) {
			return 0, false
		}
		return int(v), true
	}
	var st WindowState
	var ok bool
	if st.Width, ok = num("width"); !ok {
		return WindowState{}, false
	}
	if st.Height, ok = num("height"); !ok {
		return WindowState{}, false
	}
	if st.X, ok = num("x"); !ok {
		return WindowState{}, false
	}
	if st.Y, ok = num("y"); !ok {
		return WindowState{}, false
	}
	st.Maximized, _ = raw["maximized"].(bool)
	return st, true
}

func SaveWindowState(storageDir string, st WindowState) {
	writeJSON(WindowStatePath(storageDir), st)
}

func rectsIntersect(x, y, w, h int, s ScreenRect) bool {
	return x < s.X+s.Width && x+w > s.X && y < s.Y+s.Height && y+h > s.Y
}

// ValidateWindowState reports whether a saved geometry is a safe restore
// candidate: big enough for the window minimums and still intersecting at
// least one connected display.
func ValidateWindowState(st WindowState, screens []ScreenRect, minW, minH int) bool {
	if st.Width < minW || st.Height < minH {
		return false
	}
	for _, s := range screens {
		if rectsIntersect(st.X, st.Y, st.Width, st.Height, s) {
			return true
		}
	}
	return false
}
