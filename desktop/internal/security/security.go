// Package security ports electron/shellOrigin.js, safeExternalUrl.js and
// shellPathGuard.js: trusted origins, navigation classification and the
// filesystem jail for shell-opened paths.
package security

import (
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
)

var localBackendHosts = map[string]bool{
	"127.0.0.1": true,
	"localhost": true,
	// The Wails TLS bridge listens on loopback :9338 in front of an HTTPS
	// backend; pages served through it keep the same trust level.
	"::1": true,
}

// BackendPorts are the loopback ports the shell trusts: 9337 is the backend
// itself, 9338 the preferred app-server port. The app server may fall back
// to a random port at runtime; those are registered via
// RegisterTrustedBackendPort and accepted here.
var BackendPorts = map[string]bool{
	"9337": true,
	"9338": true,
}

var extraBackendPorts sync.Map // string -> bool

// RegisterTrustedBackendPort marks an additional loopback port as trusted
// (the app server's bound port when 9338 was busy).
func RegisterTrustedBackendPort(port string) {
	if port != "" {
		extraBackendPorts.Store(port, true)
	}
}

// UnregisterTrustedBackendPort removes a port registered at runtime (the app
// server calls this on Stop so a dead listener's port doesn't stay trusted).
func UnregisterTrustedBackendPort(port string) {
	if port != "" {
		extraBackendPorts.Delete(port)
	}
}

func trustedBackendPort(port string) bool {
	if BackendPorts[port] {
		return true
	}
	_, ok := extraBackendPorts.Load(port)
	return ok
}

func parseAbsoluteURL(raw string) *url.URL {
	if raw == "" {
		return nil
	}
	u, err := url.Parse(raw)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return nil
	}
	return u
}

func hostnameOf(u *url.URL) string {
	h := strings.ToLower(u.Hostname())
	h = strings.TrimPrefix(h, "[")
	h = strings.TrimSuffix(h, "]")
	return h
}

func portOf(u *url.URL) string {
	if u.Port() != "" {
		return u.Port()
	}
	if u.Scheme == "https" {
		return "443"
	}
	return "80"
}

// IsLocalBackendURL reports whether raw is an absolute http(s) URL on a
// loopback host at a trusted backend port, with no userinfo (so
// http://127.0.0.1:9337@example.com is NOT local).
func IsLocalBackendURL(raw string) bool {
	u := parseAbsoluteURL(raw)
	if u == nil {
		return false
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return false
	}
	if u.User != nil && (u.User.Username() != "" || u.User.String() != "") {
		return false
	}
	if !localBackendHosts[hostnameOf(u)] {
		return false
	}
	return trustedBackendPort(portOf(u))
}

// blobInnerHTTPURL returns the inner http(s) URL of a blob: URL, or "".
func blobInnerHTTPURL(raw string) string {
	if !strings.HasPrefix(raw, "blob:") {
		return ""
	}
	inner := raw[len("blob:"):]
	u := parseAbsoluteURL(inner)
	if u == nil || (u.Scheme != "http" && u.Scheme != "https") {
		return ""
	}
	return inner
}

// IsTrustedBlobURL reports whether raw is a blob: URL whose inner URL is a
// trusted local backend URL (print preview windows).
func IsTrustedBlobURL(raw string) bool {
	inner := blobInnerHTTPURL(raw)
	return inner != "" && IsLocalBackendURL(inner)
}

// WailsAssetOrigins are the embedded-asset origins per platform.
// Linux/macOS serve assets over the wails:// scheme; Windows over
// http(s)://wails.localhost.
func WailsAssetOrigins() []string {
	switch runtime.GOOS {
	case "windows":
		return []string{"http://wails.localhost", "https://wails.localhost"}
	case "android":
		return []string{"https://wails.localhost"}
	default:
		return []string{"wails://localhost"}
	}
}

func isWailsAssetURL(raw string) bool {
	u := parseAbsoluteURL(raw)
	if u == nil {
		return false
	}
	for _, origin := range WailsAssetOrigins() {
		ou, err := url.Parse(origin)
		if err != nil {
			continue
		}
		if strings.EqualFold(u.Scheme, ou.Scheme) && strings.EqualFold(u.Host, ou.Host) {
			return true
		}
	}
	return false
}

// IsTrustedShellPageURL reports whether raw is a shell page URL: either a
// Wails asset URL for an embedded dialog page (loading/crash/close-dialog/
// prompt served by the asset server) or an app-server /__shell/*.html page
// (loading/crash served by the loopback app server).
func IsTrustedShellPageURL(raw string) bool {
	u := parseAbsoluteURL(raw)
	if u == nil {
		return false
	}
	if IsAppShellPageURL(raw) {
		return true
	}
	if !isWailsAssetURL(raw) {
		return false
	}
	p := strings.ToLower(u.Path)
	return strings.HasSuffix(p, "/loading.html") || strings.HasSuffix(p, "/crash.html") ||
		strings.HasSuffix(p, "/close-dialog.html") || strings.HasSuffix(p, "/prompt.html") ||
		strings.HasSuffix(p, "/serial-picker.html")
}

// ShellAssetPathPrefix is the app-server path prefix for embedded shell
// assets (loading/crash pages and their JS/CSS/images).
const ShellAssetPathPrefix = "/__shell/"

// IsAppShellAssetPath reports whether the URL path is under /__shell/.
func IsAppShellAssetPath(u *url.URL) bool {
	return u != nil && strings.HasPrefix(u.Path, ShellAssetPathPrefix)
}

// IsAppShellPageURL reports whether raw is an app-server URL for an
// embedded shell HTML page (loading/crash/idle etc. under /__shell/).
func IsAppShellPageURL(raw string) bool {
	u := parseAbsoluteURL(raw)
	if u == nil || !IsLocalBackendURL(raw) || !IsAppShellAssetPath(u) {
		return false
	}
	return strings.HasSuffix(strings.ToLower(u.Path), ".html")
}

// IsAppPageURL reports whether raw is a proxied backend app page (a trusted
// local backend URL that is NOT a shell asset).
func IsAppPageURL(raw string) bool {
	u := parseAbsoluteURL(raw)
	if u == nil || !IsLocalBackendURL(raw) {
		return false
	}
	return !IsAppShellAssetPath(u)
}

// IsTrustedShellOrigin is the JS->Go trust gate: Wails asset pages, the local
// backend, and trusted local blobs.
func IsTrustedShellOrigin(raw string) bool {
	if raw == "" {
		return false
	}
	if isWailsAssetURL(raw) {
		return true
	}
	if IsTrustedBlobURL(raw) {
		return true
	}
	return IsLocalBackendURL(raw)
}

// PageKind classifies the main window's current page for backend lifecycle
// routing ("loading" | "crash" | "app" | "other" | "none").
func PageKind(currentURL string, windowExists bool) string {
	if !windowExists || currentURL == "" {
		return "none"
	}
	// App-server shell pages live on the same origin as the app; classify
	// them by path before the generic local-backend check.
	if u := parseAbsoluteURL(currentURL); u != nil && IsLocalBackendURL(currentURL) && IsAppShellAssetPath(u) {
		p := strings.ToLower(u.Path)
		switch {
		case strings.HasSuffix(p, "/loading.html"):
			return "loading"
		case strings.HasSuffix(p, "/crash.html"):
			return "crash"
		default:
			return "other"
		}
	}
	if IsTrustedShellPageURL(currentURL) {
		u := parseAbsoluteURL(currentURL)
		p := strings.ToLower(u.Path)
		switch {
		case strings.HasSuffix(p, "/loading.html"):
			return "loading"
		case strings.HasSuffix(p, "/crash.html"):
			return "crash"
		default:
			return "other"
		}
	}
	if IsAppPageURL(currentURL) {
		return "app"
	}
	return "other"
}

// ShouldOpenInChildWindow reports whether window.open should create a Wails
// child window instead of the OS browser: local backend popouts, call.html,
// translator hashes and trusted local blobs.
func ShouldOpenInChildWindow(raw string) bool {
	if raw == "" {
		return false
	}
	if strings.HasPrefix(raw, "blob:") {
		return IsTrustedBlobURL(raw)
	}
	if !IsLocalBackendURL(raw) {
		return false
	}
	u := parseAbsoluteURL(raw)
	if u == nil {
		return false
	}
	p := u.Path
	if p == "/call.html" || strings.HasSuffix(p, "/call.html") {
		return true
	}
	hash := u.Fragment
	if strings.HasPrefix(hash, "/translator") {
		return true
	}
	return strings.HasPrefix(hash, "/popout/")
}

// ShouldAllowInWindowNavigation reports whether the main frame may navigate to
// raw inside the shell. External http(s) must go to the OS browser; data:,
// file: and untrusted blob: are denied.
func ShouldAllowInWindowNavigation(raw string) bool {
	if raw == "" {
		return false
	}
	if strings.HasPrefix(raw, "blob:") {
		return IsTrustedBlobURL(raw)
	}
	return IsLocalBackendURL(raw)
}

// NormalizeExternalURLForOpen returns a normalized http(s) or mailto URL for
// the OS browser, or "" when the input must not reach the OS shell.
func NormalizeExternalURLForOpen(raw string) string {
	if raw == "" {
		return ""
	}
	s := strings.TrimSpace(raw)
	if s == "" {
		return ""
	}
	u, err := url.Parse(s)
	if err != nil || u.Scheme == "" {
		return ""
	}
	switch u.Scheme {
	case "http", "https":
		if u.User != nil && (u.User.Username() != "" || u.User.String() != "") {
			return ""
		}
		return u.String()
	case "mailto":
		return u.String()
	}
	return ""
}

// ---- shellPathGuard.js port ----------------------------------------------

func resolveDirForPrefixCheck(dir string) string {
	if real, err := filepath.EvalSymlinks(dir); err == nil {
		return real
	}
	abs, err := filepath.Abs(dir)
	if err != nil {
		return dir
	}
	return abs
}

func realpathOrNearest(target string) string {
	current := target
	if abs, err := filepath.Abs(current); err == nil {
		current = abs
	}
	var tail []string
	for depth := 0; depth < 64; depth++ {
		if real, err := filepath.EvalSymlinks(current); err == nil {
			if len(tail) == 0 {
				return real
			}
			parts := append([]string{real}, reverseStrings(tail)...)
			return filepath.Join(parts...)
		}
		parent := filepath.Dir(current)
		if parent == current {
			abs, _ := filepath.Abs(target)
			return abs
		}
		tail = append(tail, filepath.Base(current))
		current = parent
	}
	abs, _ := filepath.Abs(target)
	return abs
}

func reverseStrings(in []string) []string {
	out := make([]string, len(in))
	for i, v := range in {
		out[len(in)-1-i] = v
	}
	return out
}

func isResolvedPathUnderRoot(resolvedCandidate, root string) bool {
	rootReal := resolveDirForPrefixCheck(root)
	fileReal := realpathOrNearest(resolvedCandidate)
	rel, err := filepath.Rel(rootReal, fileReal)
	if err != nil {
		return false
	}
	if rel == "" {
		return true
	}
	return rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

func pairedLegacyStorageDir(defaultStorageDir string) string {
	abs := filepath.Clean(defaultStorageDir)
	base := filepath.Base(abs)
	if !strings.EqualFold(base, ".reticulum-meshchatx") {
		return ""
	}
	return filepath.Join(filepath.Dir(abs), ".reticulum-meshchat")
}

// PathGuardRoots are the directories the shell may reveal/open. Computed once
// at startup from the resolved storage roots and standard user folders.
type PathGuardRoots struct {
	StorageDir            string
	ReticulumConfigDir    string
	UserDataDir           string
	DownloadsDir          string
	DocumentsDir          string
	PicturesDir           string
	TempDir               string
	PortableExecutableDir string
	UserArgv              []string
	HomeDir               string

	// blessed holds exact paths returned by native file pickers, which can
	// live outside every guarded root (e.g. ~/Desktop). Each entry is
	// single-use: ConsumeBlessedPath deletes it on match.
	blessedMu sync.Mutex
	blessed   map[string]bool
}

func (r *PathGuardRoots) roots(broadRoots bool) []string {
	var roots []string
	add := func(p string) {
		if p != "" {
			roots = append(roots, p)
		}
	}
	add(r.StorageDir)
	add(pairedLegacyStorageDir(r.StorageDir))
	add(r.ReticulumConfigDir)
	add(r.UserDataDir)
	add(filepath.Join(r.DownloadsDir, "MeshChatX"))
	add(filepath.Join(r.DocumentsDir, "MeshChatX"))
	add(filepath.Join(r.PicturesDir, "MeshChatX"))
	if broadRoots {
		add(r.TempDir)
		add(r.DownloadsDir)
		add(r.DocumentsDir)
	}
	add(r.PortableExecutableDir)
	add(ParseArgvFlagDir(r.UserArgv, "--storage-dir"))
	add(ParseArgvFlagDir(r.UserArgv, "--reticulum-config-dir"))
	dataDir := ParseArgvFlagDir(r.UserArgv, "--data-dir")
	if dataDir == "" {
		dataDir = strings.TrimSpace(os.Getenv("MESHCHAT_DATA_DIR"))
	}
	if dataDir != "" {
		add(filepath.Join(dataDir, "storage"))
		add(filepath.Join(dataDir, ".reticulum"))
	}
	return roots
}

func ParseArgvFlagDir(argv []string, flag string) string {
	v := ParseArgvFlagForPaths(argv, flag)
	if v == "" {
		return ""
	}
	if abs, err := filepath.Abs(v); err == nil {
		return abs
	}
	return v
}

// ParseArgvFlagForPaths is ParseArgvFlag re-exported for this package.
func ParseArgvFlagForPaths(argv []string, flagName string) string {
	prefix := flagName + "="
	for _, arg := range argv {
		if strings.HasPrefix(arg, prefix) {
			v := arg[len(prefix):]
			if v != "" {
				return v
			}
			return ""
		}
	}
	for i, arg := range argv {
		if arg == flagName && i+1 < len(argv) {
			v := argv[i+1]
			if v != "" && !strings.HasPrefix(v, "--") {
				return v
			}
			return ""
		}
	}
	return ""
}

// BlessPath marks an exact path as allowed for one ConsumeBlessedPath check.
// Only native picker results should be blessed — never JS-supplied strings.
func (r *PathGuardRoots) BlessPath(path string) {
	resolved := path
	if abs, err := filepath.Abs(strings.TrimSpace(path)); err == nil {
		resolved = abs
	}
	r.blessedMu.Lock()
	if r.blessed == nil {
		r.blessed = map[string]bool{}
	}
	r.blessed[resolved] = true
	r.blessedMu.Unlock()
}

// ConsumeBlessedPath reports whether path was blessed via BlessPath and
// clears the blessing so it cannot be reused.
func (r *PathGuardRoots) ConsumeBlessedPath(path string) bool {
	resolved := path
	if abs, err := filepath.Abs(strings.TrimSpace(path)); err == nil {
		resolved = abs
	}
	r.blessedMu.Lock()
	defer r.blessedMu.Unlock()
	if !r.blessed[resolved] {
		return false
	}
	delete(r.blessed, resolved)
	return true
}

// IsAllowedShellPath reports whether targetPath is inside an allowed root.
// broadRoots=false restricts to app-owned roots (used by open-path execution).
func (r *PathGuardRoots) IsAllowedShellPath(targetPath string, broadRoots bool) bool {
	if targetPath == "" || strings.TrimSpace(targetPath) == "" {
		return false
	}
	if strings.ContainsRune(targetPath, 0) {
		return false
	}
	resolved := targetPath
	if abs, err := filepath.Abs(strings.TrimSpace(targetPath)); err == nil {
		resolved = abs
	}
	for _, root := range r.roots(broadRoots) {
		if root != "" && isResolvedPathUnderRoot(resolved, root) {
			return true
		}
	}
	return false
}

// UserDirs returns the standard user directories used by the path guard.
func UserDirs() (downloads, documents, pictures, temp string) {
	home, _ := os.UserHomeDir()
	downloads = filepath.Join(home, "Downloads")
	documents = filepath.Join(home, "Documents")
	pictures = filepath.Join(home, "Pictures")
	temp = os.TempDir()
	if runtime.GOOS == "windows" {
		if v := os.Getenv("USERPROFILE"); v != "" {
			downloads = filepath.Join(v, "Downloads")
			documents = filepath.Join(v, "Documents")
			pictures = filepath.Join(v, "Pictures")
		}
		if v := os.Getenv("TEMP"); v != "" {
			temp = v
		}
	}
	return
}
