package paths

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestParseArgvFlag(t *testing.T) {
	argv := []string{"app", "--storage-dir", "/tmp/a b", "--headless", "--port=9337"}
	if got := ParseArgvFlag(argv, "--storage-dir"); got != "/tmp/a b" {
		t.Fatalf("space value: %q", got)
	}
	if got := ParseArgvFlag(argv, "--port"); got != "9337" {
		t.Fatalf("equals form: %q", got)
	}
	if got := ParseArgvFlag(argv, "--missing"); got != "" {
		t.Fatalf("missing: %q", got)
	}
	// flag-like next arg is not a value
	if got := ParseArgvFlag([]string{"--headless", "--x"}, "--headless"); got != "" {
		t.Fatalf("flag-as-value: %q", got)
	}
}

func TestHasArgvFlag(t *testing.T) {
	argv := []string{"--headless", "--no-https", "x"}
	if !HasArgvFlag(argv, "--headless") || !HasArgvFlag(argv, "--no-https") {
		t.Fatal("flags should be found")
	}
	if HasArgvFlag(argv, "--https") {
		t.Fatal("absent flag found")
	}
}

func TestFindProtocolUrlArg(t *testing.T) {
	if got := FindProtocolUrlArg([]string{"app", "lxmf://abc/def"}); got != "lxmf://abc/def" {
		t.Fatalf("protocol arg: %q", got)
	}
	if got := FindProtocolUrlArg([]string{"app", "https://x"}); got != "" {
		t.Fatalf("non-protocol: %q", got)
	}
}

func TestIsProtocolURL(t *testing.T) {
	for _, u := range []string{"lxmf://abc", "LXMf://a/b?x=1", "rns://n/1"} {
		if !IsProtocolURL(u) {
			t.Errorf("should accept %q", u)
		}
	}
	for _, u := range []string{"https://x", "file:///etc/passwd", "javascript:alert(1)", "lxmf:", "", "http://lxmf://x"} {
		if IsProtocolURL(u) {
			t.Errorf("should reject %q", u)
		}
	}
}

func TestGetUserProvidedArguments(t *testing.T) {
	// GPU/sandbox noise flags and deep links are stripped; the rest are kept
	argv := []string{"exe", "--no-sandbox", "--disable-gpu", "lxmf://a/b", "--my-flag", "v", "--storage-dir", "/s"}
	got := GetUserProvidedArguments(argv)
	joined := " " + joinStr(got, " ") + " "
	for _, gone := range []string{"--no-sandbox", "--disable-gpu", "lxmf://a/b"} {
		if contains(joined, gone) {
			t.Fatalf("%s should be stripped: %v", gone, got)
		}
	}
	for _, kept := range []string{"--my-flag", "v", "--storage-dir", "/s"} {
		if !contains(joined, kept) {
			t.Fatalf("%s should be kept: %v", kept, got)
		}
	}
}

func joinStr(s []string, sep string) string {
	out := ""
	for i, v := range s {
		if i > 0 {
			out += sep
		}
		out += v
	}
	return out
}

func contains(haystack, needle string) bool {
	return len(needle) > 0 && (haystack == needle || len(haystack) > len(needle) &&
		(func() bool {
			for i := 0; i+len(needle) <= len(haystack); i++ {
				if haystack[i:i+len(needle)] == needle {
					return true
				}
			}
			return false
		})())
}

func TestArchSegment(t *testing.T) {
	want := map[string]string{"amd64": "x64", "arm64": "arm64"}
	if got := ArchSegment(); got != want[runtime.GOARCH] {
		t.Fatalf("arch: got %q want %q", got, want[runtime.GOARCH])
	}
}

func TestPlatformFolder(t *testing.T) {
	want := map[string]string{"linux": "linux", "windows": "win32", "darwin": "darwin"}
	if got := PlatformFolder(); got != want[runtime.GOOS] {
		t.Fatalf("platform: got %q want %q", got, want[runtime.GOOS])
	}
}

func TestFindBackendExecutable(t *testing.T) {
	dir := t.TempDir()
	backendDir := filepath.Join(dir, "backend")
	mustMkdir(t, backendDir)
	exeName := "ReticulumMeshChatX"
	if runtime.GOOS == "windows" {
		exeName += ".exe"
	}
	p := filepath.Join(backendDir, exeName)
	mustWrite(t, p)
	got, checked := FindBackendExecutable(filepath.Join(dir, "meshchatx-desktop"), "", "")
	if got != p {
		t.Fatalf("found %q checked %v", got, checked)
	}
}

func mustMkdir(t *testing.T, p string) {
	t.Helper()
	if err := os.MkdirAll(p, 0o755); err != nil {
		t.Fatal(err)
	}
}

func mustWrite(t *testing.T, p string) {
	t.Helper()
	if err := os.WriteFile(p, []byte("x"), 0o755); err != nil {
		t.Fatal(err)
	}
}
