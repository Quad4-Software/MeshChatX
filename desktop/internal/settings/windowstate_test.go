package settings

import (
	"os"
	"path/filepath"
	"testing"
)

var testScreens = []ScreenRect{
	{X: 0, Y: 0, Width: 1920, Height: 1080},
	{X: 1920, Y: 0, Width: 1920, Height: 1080},
}

func TestValidateWindowState(t *testing.T) {
	cases := []struct {
		name string
		st   WindowState
		minW int
		minH int
		scrs []ScreenRect
		want bool
	}{
		{"valid primary", WindowState{Width: 1280, Height: 800, X: 100, Y: 100}, 900, 600, testScreens, true},
		{"valid second screen", WindowState{Width: 1280, Height: 800, X: 2000, Y: 100}, 900, 600, testScreens, true},
		{"too small", WindowState{Width: 800, Height: 800, X: 100, Y: 100}, 900, 600, testScreens, false},
		{"off all screens", WindowState{Width: 1280, Height: 800, X: -3000, Y: -3000}, 900, 600, testScreens, false},
		{"edge intersect", WindowState{Width: 1280, Height: 800, X: 1910, Y: 100}, 900, 600, testScreens, true},
		{"no screens", WindowState{Width: 1280, Height: 800, X: 0, Y: 0}, 900, 600, nil, false},
		{"maximized ignored pos", WindowState{Width: 1280, Height: 800, X: -5000, Y: -5000, Maximized: true}, 900, 600, testScreens, false},
	}
	for _, c := range cases {
		if got := ValidateWindowState(c.st, c.scrs, c.minW, c.minH); got != c.want {
			t.Errorf("%s: got %v want %v", c.name, got, c.want)
		}
	}
}

func TestWindowStateRoundTrip(t *testing.T) {
	dir := t.TempDir()
	if _, ok := LoadWindowState(dir); ok {
		t.Fatal("expected no state")
	}
	st := WindowState{Width: 1440, Height: 900, X: 50, Y: 60, Maximized: true}
	SaveWindowState(dir, st)
	got, ok := LoadWindowState(dir)
	if !ok || got != st {
		t.Fatalf("got %+v ok=%v", got, ok)
	}
	if _, err := os.Stat(filepath.Join(dir, "desktop-window-state.json")); err != nil {
		t.Fatal(err)
	}
}

func TestLoadWindowStateCorrupt(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(WindowStatePath(dir), []byte("{bad"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, ok := LoadWindowState(dir); ok {
		t.Fatal("corrupt file should not load")
	}
	if err := os.WriteFile(WindowStatePath(dir), []byte(`{"width":"x"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, ok := LoadWindowState(dir); ok {
		t.Fatal("wrong types should not load")
	}
}
