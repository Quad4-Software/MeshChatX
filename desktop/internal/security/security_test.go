package security

import (
	"path/filepath"
	"testing"
)

func TestIsLocalBackendURL(t *testing.T) {
	good := []string{
		"http://127.0.0.1:9337/",
		"http://localhost:9337/api/v1/status",
		"https://127.0.0.1:9338/x",
		"http://[::1]:9337/",
	}
	for _, u := range good {
		if !IsLocalBackendURL(u) {
			t.Errorf("should be local backend: %s", u)
		}
	}
	bad := []string{
		"http://127.0.0.1:9999/",          // wrong port
		"http://127.0.0.1:9337.evil.com/", // lookalike host
		"http://evil.com:9337/",
		"http://user@127.0.0.1:9337/", // userinfo
		"ftp://127.0.0.1:9337/",
		"file:///etc/passwd",
		"http://192.168.1.5:9337/", // non-loopback
		"not a url",
		"",
	}
	for _, u := range bad {
		if IsLocalBackendURL(u) {
			t.Errorf("should NOT be local backend: %s", u)
		}
	}
}

func TestIsTrustedBlobURL(t *testing.T) {
	if !IsTrustedBlobURL("blob:http://127.0.0.1:9337/abc-123") {
		t.Error("trusted backend blob should pass")
	}
	if IsTrustedBlobURL("blob:https://evil.com/abc") {
		t.Error("external blob should fail")
	}
	if IsTrustedBlobURL("blob:http://127.0.0.1:9999/abc") {
		t.Error("wrong-port blob should fail")
	}
	if IsTrustedBlobURL("blob:notaurl") {
		t.Error("malformed blob should fail")
	}
}

func TestShouldOpenInChildWindow(t *testing.T) {
	cases := []struct {
		raw  string
		want bool
	}{
		{"http://127.0.0.1:9337/call.html", true},
		{"http://localhost:9337/call.html?x=1", true},
		{"http://127.0.0.1:9337/#/popout/abc", true},
		{"http://127.0.0.1:9337/#/translator/en", true},
		{"blob:http://127.0.0.1:9337/uuid", true},
		{"http://127.0.0.1:9337/", false},
		{"http://127.0.0.1:9337/index.html", false},
		{"https://example.com/call.html", false},
		{"", false},
	}
	for _, tc := range cases {
		if got := ShouldOpenInChildWindow(tc.raw); got != tc.want {
			t.Errorf("%s: got %v want %v", tc.raw, got, tc.want)
		}
	}
}

func TestShouldAllowInWindowNavigation(t *testing.T) {
	if !ShouldAllowInWindowNavigation("http://127.0.0.1:9337/app") {
		t.Error("local backend nav should be allowed")
	}
	if ShouldAllowInWindowNavigation("https://example.com/") {
		t.Error("external nav must be denied (goes to browser)")
	}
	if ShouldAllowInWindowNavigation("file:///etc/passwd") {
		t.Error("file: must be denied")
	}
	if ShouldAllowInWindowNavigation("blob:https://evil.com/x") {
		t.Error("untrusted blob must be denied")
	}
}

func TestIsTrustedShellPageURL(t *testing.T) {
	for _, u := range WailsAssetOrigins() {
		if !IsTrustedShellPageURL(u + "/loading.html") {
			t.Errorf("asset origin page should be trusted: %s", u)
		}
	}
	if IsTrustedShellPageURL("https://evil.com/loading.html") {
		t.Error("external page must not be trusted")
	}
}

func TestNormalizeExternalURLForOpen(t *testing.T) {
	if got := NormalizeExternalURLForOpen("https://example.com/x"); got != "https://example.com/x" {
		t.Fatalf("https: %q", got)
	}
	if got := NormalizeExternalURLForOpen("mailto:a@b.c"); got != "mailto:a@b.c" {
		t.Fatalf("mailto: %q", got)
	}
	for _, bad := range []string{"file:///etc/passwd", "javascript:alert(1)", "data:text/html,x", "http://user@x.com/", ""} {
		if got := NormalizeExternalURLForOpen(bad); got != "" {
			t.Errorf("%q should be rejected, got %q", bad, got)
		}
	}
}

func TestPageKind(t *testing.T) {
	if got := PageKind("wails://localhost/loading.html", true); got != "loading" {
		t.Fatalf("loading: %q", got)
	}
	if got := PageKind("http://127.0.0.1:9337/", true); got != "app" {
		t.Fatalf("app: %q", got)
	}
	if got := PageKind("http://127.0.0.1:9337/", false); got != "none" {
		t.Fatalf("no window: %q", got)
	}
}

func TestUnregisterTrustedBackendPort(t *testing.T) {
	const port = "59997"
	RegisterTrustedBackendPort(port)
	if !IsLocalBackendURL("http://127.0.0.1:" + port + "/x") {
		t.Fatal("registered port should be trusted")
	}
	UnregisterTrustedBackendPort(port)
	if IsLocalBackendURL("http://127.0.0.1:" + port + "/x") {
		t.Fatal("unregistered port should not be trusted")
	}
}

func TestBlessedPathSingleUse(t *testing.T) {
	r := &PathGuardRoots{StorageDir: t.TempDir()}
	picked := filepath.Join(t.TempDir(), "backup.zip") // outside every guarded root
	if r.IsAllowedShellPath(picked, true) {
		t.Fatal("unblessed outside path should not be allowed")
	}
	r.BlessPath(picked)
	if !r.ConsumeBlessedPath(picked) {
		t.Fatal("blessed path should be consumed once")
	}
	if r.ConsumeBlessedPath(picked) {
		t.Fatal("blessing must be single-use")
	}
	if r.ConsumeBlessedPath(filepath.Join(t.TempDir(), "other.zip")) {
		t.Fatal("unblessed path consumed")
	}
}

func TestAppServerPageClassification(t *testing.T) {
	RegisterTrustedBackendPort("59999")
	cases := []struct {
		raw  string
		want string
	}{
		{"http://127.0.0.1:9338/__shell/loading.html?theme=dark", "loading"},
		{"http://127.0.0.1:59999/__shell/crash.html", "crash"},
		{"http://127.0.0.1:59999/__shell/idle.html", "other"},
		{"http://127.0.0.1:59999/?nocache=1", "app"},
		{"http://127.0.0.1:9337/api/v1/status", "app"},
		{"http://127.0.0.1:59998/x", "other"}, // unregistered port
	}
	for _, c := range cases {
		if got := PageKind(c.raw, true); got != c.want {
			t.Fatalf("PageKind(%q) = %q, want %q", c.raw, got, c.want)
		}
	}
	if !IsTrustedShellPageURL("http://127.0.0.1:9338/__shell/loading.html") {
		t.Fatal("app-server loading page not trusted")
	}
	if !IsAppShellPageURL("http://127.0.0.1:9338/__shell/crash.html") {
		t.Fatal("app-server crash page not classified")
	}
}
