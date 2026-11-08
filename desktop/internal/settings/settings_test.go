package settings

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestResolveCloseAction(t *testing.T) {
	cases := []struct {
		name string
		in   CloseSettings
		want string
	}{
		{"ask", CloseSettings{CloseBehavior: "ask", TrayEnabled: true}, "ask"},
		{"quit", CloseSettings{CloseBehavior: "quit", TrayEnabled: true}, "quit"},
		{"background w/ tray", CloseSettings{CloseBehavior: "background", TrayEnabled: true}, "background"},
		{"background w/o tray -> minimize", CloseSettings{CloseBehavior: "background", TrayEnabled: false}, "minimize"},
		{"unknown normalizes to ask", CloseSettings{CloseBehavior: "bogus", TrayEnabled: true}, "ask"},
		{"empty -> ask", CloseSettings{}, "ask"},
	}
	for _, tc := range cases {
		if got := ResolveCloseAction(tc.in); got != tc.want {
			t.Errorf("%s: got %q want %q", tc.name, got, tc.want)
		}
	}
}

func TestRememberedCloseSettings(t *testing.T) {
	if got := RememberedCloseSettings("quit", true); got["closeBehavior"] != "quit" {
		t.Fatalf("quit+remember: %v", got)
	}
	if got := RememberedCloseSettings("background", true); got["closeBehavior"] != "background" {
		t.Fatalf("background+remember: %v", got)
	}
	if got := RememberedCloseSettings("quit", false); got != nil {
		t.Fatalf("no remember should be nil: %v", got)
	}
	if got := RememberedCloseSettings("ask", true); got != nil {
		t.Fatalf("ask should be nil: %v", got)
	}
}

func TestNormalizeCloseSettings(t *testing.T) {
	got := NormalizeCloseSettings(map[string]any{
		"closeBehavior": "quit",
		"trayEnabled":   false,
		"extra":         "drop",
	})
	if got.CloseBehavior != "quit" || got.TrayEnabled {
		t.Fatalf("got %+v", got)
	}
	if got := NormalizeCloseSettings(map[string]any{"closeBehavior": "bogus"}); got.CloseBehavior != "ask" {
		t.Fatalf("bogus should default ask: %+v", got)
	}
}

func TestCloseSettingsRoundTrip(t *testing.T) {
	dir := t.TempDir()
	SaveCloseSettings(dir, map[string]any{"closeBehavior": "quit", "trayEnabled": false})
	got := LoadCloseSettings(dir)
	if got.CloseBehavior != "quit" || got.TrayEnabled {
		t.Fatalf("roundtrip: %+v", got)
	}
	data, _ := os.ReadFile(CloseSettingsPath(dir))
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		t.Fatal(err)
	}
	if _, ok := raw["extra"]; ok {
		t.Fatal("unexpected keys persisted")
	}
}

func TestUiTheme(t *testing.T) {
	if got := NormalizeUiThemePreference("dark"); got != "dark" {
		t.Fatalf("dark: %q", got)
	}
	if got := NormalizeUiThemePreference("bogus"); got != "system" {
		t.Fatalf("bogus should be system: %q", got)
	}
	if got := ResolveEffectiveUiTheme("dark", false); got != "dark" {
		t.Fatalf("explicit dark wins: %q", got)
	}
	if got := ResolveEffectiveUiTheme("system", true); got != "dark" {
		t.Fatalf("system+dark pref: %q", got)
	}
	if got := ResolveEffectiveUiTheme("system", false); got != "light" {
		t.Fatalf("system+light pref: %q", got)
	}
	dir := t.TempDir()
	SaveUiThemePreference(dir, "dark")
	if got := LoadUiThemePreference(dir); got != "dark" {
		t.Fatalf("load: %q", got)
	}
}

func TestDesktopPrivacySettings(t *testing.T) {
	dir := t.TempDir()
	def := DefaultDesktopPrivacySettings()
	SaveDesktopPrivacySettings(dir, map[string]any{"screenSecurityEnabled": true})
	got := LoadDesktopPrivacySettings(dir)
	if !got.ScreenSecurityEnabled {
		t.Fatalf("screen security not persisted: %+v", got)
	}
	_ = def
	// unsupported platform
	if IsScreenSecurityPlatformSupported("linux") {
		t.Fatal("linux should not support screen security")
	}
	if !IsScreenSecurityPlatformSupported("windows") {
		t.Fatal("windows should support screen security")
	}
	if !IsScreenSecurityPlatformSupported("darwin") {
		t.Fatal("darwin should support screen security")
	}
}

func TestCloseRequestGuardConcurrent(t *testing.T) {
	var g CloseRequestGuard
	var inFlight atomic.Int32
	var maxSeen atomic.Int32
	var wg sync.WaitGroup
	for i := 0; i < 32; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if g.TryEnter() {
				cur := inFlight.Add(1)
				for {
					old := maxSeen.Load()
					if cur <= old || maxSeen.CompareAndSwap(old, cur) {
						break
					}
				}
				time.Sleep(time.Millisecond)
				inFlight.Add(-1)
				g.Leave()
			}
		}()
	}
	wg.Wait()
	if got := maxSeen.Load(); got != 1 {
		t.Fatalf("guard allowed %d concurrent holders, want 1", got)
	}
	if !g.TryEnter() {
		t.Fatal("guard stuck after Leave")
	}
	g.Leave()
}

func TestUiThemePath(t *testing.T) {
	if filepath.Base(UiThemePath("/x")) != "desktop-ui-theme.json" {
		t.Fatalf("path: %s", UiThemePath("/x"))
	}
}
