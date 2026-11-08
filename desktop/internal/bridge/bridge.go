// Package bridge implements the JS<->Go RPC over Wails' RawMessageHandler.
// The renderer posts {v:1,id,method,args} JSON through the native
// postMessage channel; Go replies via window.ExecJS calling
// window.__desktopBridge.resolve / .emit (see desktop/shell/desktop-bridge.js).
// Method names match the old Electron IPC channels 1:1.
package bridge

import (
	"crypto/rand"
	"crypto/subtle"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/backendproc"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/crashreport"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/integrity"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/security"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/serial"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/settings"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/system"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/updateapply"
)

// Deps wires the bridge to the running application.
type Deps struct {
	// Window access.
	MainWindow      func() application.Window
	WindowByName    func(name string) application.Window
	AllWindows      func() []application.Window
	PageKind        func() string
	ShowMainWindow  func()
	FocusMainWindow func()

	// App services.
	StorageDir             func() string
	DownloadsDir           func() string
	ReticulumConfigDir     func() string
	UserProvidedArgs       func() []string
	IntegrityStatus        func() *integrity.Result
	SetIntegrityStatus     func(r integrity.Result)
	Backend                *backendproc.Manager
	AppVersion             func() string
	WailsVersion           func() string
	IsHardwareAccel        func() bool
	WebViewKind            func() string
	Quit                   func()
	Relaunch               func(extraArgs ...string)
	ApplyUpdateAndExit     func()
	OpenExternal           func(rawURL string) bool
	OpenChildWindow        func(spec ChildWindowSpec) (application.Window, error)
	CloseChildWindow       func(name string)
	NotifyShow             func(title, body string, silent bool, destinationHash string)
	NotifyClose            func(destinationHash *string) int
	PowerSaveBlocker       system.PowerSaveBlocker
	PickFile               func() (string, error)
	PickDirectory          func() (string, error)
	PickDatabaseBackup     func() (string, error)
	RevealPath             func(path string)
	OpenPath               func(path string) string
	PathGuard              *security.PathGuardRoots
	ShowMessage            func(kind, title, message string) int // 0=cancel/close,1=ok
	ConfirmDialog          func(message string) bool
	PromptDialog           func(message, def string) (string, bool)
	SetContentProtection   func(enabled bool)
	PrivacyPlatform        func() string
	SetUiTheme             func(pref string) (saved, effective string)
	GetUiTheme             func() (pref, effective string)
	IsHeadless             func() bool
	SetWindowURL           func(win application.Window, rawurl string)
	AppURL                 func() string
	ShowCrashPage          func(crash map[string]any)
	OnCloseSettingsChanged func()
	OnUiThemeChanged       func(effective string)
	Log                    func(msg string)

	// Serial bridge (navigator.serial polyfill). PickSerialPort opens the
	// native picker window and resolves with the chosen port's JSON or "".
	Serial         *serial.Manager
	PickSerialPort func(filtersJSON string) (resultJSON string, ok bool)
}

// ChildWindowSpec describes a requested popout window.
type ChildWindowSpec struct {
	URL    string `json:"url"`
	Target string `json:"target"`
	Width  int    `json:"width"`
	Height int    `json:"height"`
}

// Bridge dispatches raw messages.
type Bridge struct {
	deps Deps

	mu             sync.Mutex
	pendingWindows map[string]*pendingWindow
	downloads      *DownloadManager
	probeClient    *http.Client
	tokens         sync.Map // window ID string -> current page-load token
}

// pendingWindow is a window-result rendezvous bound to the Wails window that
// owns it, so only that window can resolve it (fixed names like
// "prompt-dialog" are not secrets).
type pendingWindow struct {
	ch       chan string
	windowID uint
}

// RotateToken issues a fresh per-page-load capability token for a window and
// pushes it to the TOP frame only via ExecJS (main frame). Called on every
// page load finish so tokens from replaced pages go stale automatically.
func (b *Bridge) RotateToken(window application.Window) {
	if window == nil {
		return
	}
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return
	}
	token := hex.EncodeToString(buf)
	b.tokens.Store(window.ID(), token)
	b.downloads.AbortForWindow(window.ID())
	js := fmt.Sprintf("window.__desktopBridge&&window.__desktopBridge.__init(%s)", mustJSONString(token))
	window.ExecJS(js)
}

// InvalidateWindow drops the window's token (window closed).
func (b *Bridge) InvalidateWindow(window application.Window) {
	if window != nil {
		b.tokens.Delete(window.ID())
		b.downloads.AbortForWindow(window.ID())
	}
}

func mustJSONString(s string) string {
	data, _ := json.Marshal(s)
	return string(data)
}

// validToken constant-time checks the message token against the window's
// current page-load token. Missing/stale tokens are rejected.
func (b *Bridge) validToken(window application.Window, token string) bool {
	if window == nil || token == "" {
		return false
	}
	cur, ok := b.tokens.Load(window.ID())
	if !ok {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(token), []byte(cur.(string))) == 1
}

func New(deps Deps) *Bridge {
	return &Bridge{
		deps:           deps,
		pendingWindows: map[string]*pendingWindow{},
		downloads: NewDownloadManager(func() string {
			if deps.DownloadsDir != nil {
				return deps.DownloadsDir()
			}
			return deps.StorageDir()
		}),
		probeClient: &http.Client{
			Timeout: 4 * time.Second,
			Transport: &http.Transport{
				TLSClientConfig: &tls.Config{InsecureSkipVerify: true}, // loopback probe only
			},
		},
	}
}

// Handle is the RawMessageHandler entry point.
func (b *Bridge) Handle(window application.Window, message string, originInfo *application.OriginInfo) {
	if originInfo == nil {
		return
	}
	// OriginInfo.IsMainFrame is only populated on macOS; on Linux/WebKitGTK
	// and Windows the origin check below is the trust gate (the bridge JS is
	// only injected into trusted pages anyway).
	origin := originInfo.Origin
	if origin == "" {
		origin = originInfo.TopOrigin
	}
	if !security.IsTrustedShellOrigin(origin) {
		b.reply(window, 0, false, map[string]any{"error": "MeshChatX desktop bridge blocked for this origin"})
		return
	}

	var req struct {
		V      int             `json:"v"`
		ID     int             `json:"id"`
		Method string          `json:"method"`
		Args   json.RawMessage `json:"args"`
		T      string          `json:"t"`
	}
	// Capability check BEFORE parsing/dispatching anything else: on Linux
	// and Windows originInfo.Origin is the TOP-LEVEL page URI, so a sandboxed
	// iframe's postMessage would otherwise inherit the trusted origin.
	// The per-load token is only known to the top frame's JS closure.
	if err := json.Unmarshal([]byte(message), &req); err != nil || req.V != 1 || req.Method == "" {
		return
	}
	if !b.validToken(window, req.T) {
		if b.deps.Log != nil {
			b.deps.Log("bridge: rejected message with invalid page token (method=" + req.Method + ")")
		}
		return
	}
	args := decodeArgs(req.Args)
	go func() {
		// A malformed message must never panic the whole shell process.
		defer func() {
			if r := recover(); r != nil && b.deps.Log != nil {
				b.deps.Log("bridge: panic in dispatch: " + fmt.Sprint(r))
			}
		}()
		b.dispatch(window, req.ID, req.Method, args)
	}()
}

func decodeArgs(raw json.RawMessage) []any {
	if len(raw) == 0 {
		return nil
	}
	var args []any
	if err := json.Unmarshal(raw, &args); err != nil {
		return nil
	}
	return args
}

func (b *Bridge) reply(window application.Window, id int, ok bool, payload any) {
	if window == nil {
		return
	}
	data, err := json.Marshal(payload)
	if err != nil {
		data = []byte(`{"error":"marshal failed"}`)
	}
	js := fmt.Sprintf("window.__desktopBridge&&window.__desktopBridge.resolve(%d,%t,%s)",
		id, ok, mustJSONString(string(data)))
	window.ExecJS(js)
}

// Emit sends an event to a window's page.
func (b *Bridge) Emit(window application.Window, name string, payload any) {
	if window == nil {
		return
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return
	}
	js := fmt.Sprintf("window.__desktopBridge&&window.__desktopBridge.emit(%s,%s)",
		mustJSONString(name), mustJSONString(string(data)))
	window.ExecJS(js)
}

// EmitMain emits an event to the main window.
func (b *Bridge) EmitMain(name string, payload any) {
	if b.deps.MainWindow == nil {
		return
	}
	b.Emit(b.deps.MainWindow(), name, payload)
}

func (b *Bridge) dispatch(window application.Window, id int, method string, args []any) {
	var result any
	var err error

	switch method {
	case "app-version":
		result = b.deps.AppVersion()
	case "runtime-info":
		result = map[string]any{
			"shell":        "wails",
			"wailsVersion": b.deps.WailsVersion(),
			"webview":      b.deps.WebViewKind(),
			"os":           runtime.GOOS,
			"arch":         runtime.GOARCH,
		}
	case "is-hardware-acceleration-enabled":
		result = b.deps.IsHardwareAccel()
	case "get-integrity-status":
		if b.deps.IntegrityStatus != nil {
			result = b.deps.IntegrityStatus()
		} else {
			result = integrity.Result{OK: true, Issues: []string{}}
		}
	case "backend-http-only":
		result = hasFlag(b.deps.UserProvidedArgs(), "--no-https")
	case "backend-runtime-state":
		if b.deps.Backend != nil {
			result = b.deps.Backend.GetRuntimeState()
		}
	case "backend-startup-diagnostics":
		if b.deps.Backend != nil {
			result = b.deps.Backend.GetStartupDiagnostics()
		}
	case "mark-backend-healthy":
		if b.deps.Backend != nil {
			b.deps.Backend.MarkBackendHealthy()
		}
		result = map[string]any{"ok": true}
	case "restart-backend":
		var ref *integrity.Result
		if b.deps.IntegrityStatus != nil {
			ref = b.deps.IntegrityStatus()
		}
		if b.deps.Backend != nil {
			result = b.deps.Backend.RestartBackend(ref)
		} else {
			result = map[string]any{"ok": false, "error": "backend unavailable"}
		}
	case "open-backend-crash-report":
		result = b.openBackendCrashReport()
	case "crash-recovery-info":
		result = b.crashRecoveryInfo()
	case "restore-database-backup":
		result = b.restoreDatabaseBackup(argString(args, 0))
	case "pick-database-backup":
		if b.deps.PickDatabaseBackup != nil {
			p, e := b.deps.PickDatabaseBackup()
			if e != nil {
				err = e
			} else {
				result = p
			}
		} else {
			result = nil
		}
	case "alert":
		if b.deps.ShowMessage != nil {
			b.deps.ShowMessage("info", "", argString(args, 0))
		}
		result = nil
	case "confirm":
		if b.deps.ConfirmDialog != nil {
			result = b.deps.ConfirmDialog(argString(args, 0))
		} else {
			result = false
		}
	case "prompt":
		if b.deps.PromptDialog != nil {
			v, ok := b.deps.PromptDialog(argString(args, 0), argString(args, 1))
			if ok {
				result = v
			} else {
				result = nil
			}
		} else {
			result = nil
		}
	case "relaunch":
		if b.deps.Relaunch != nil {
			b.deps.Relaunch()
		}
		result = nil
	case "relaunch-emergency":
		if b.deps.Relaunch != nil {
			b.deps.Relaunch("--emergency")
		}
		result = nil
	case "relaunch-auto-recover":
		if b.deps.Relaunch != nil {
			b.deps.Relaunch("--auto-recover")
		}
		result = nil
	case "update-apply":
		result = updateapply.ApplyPendingUpdate(b.deps.StorageDir())
		if m, ok := result.(map[string]any); ok {
			if applied, _ := m["applied"].(bool); applied && b.deps.ApplyUpdateAndExit != nil {
				go b.deps.ApplyUpdateAndExit()
			}
		}
	case "shutdown":
		if b.deps.Quit != nil {
			go b.deps.Quit()
		}
		result = nil
	case "get-close-settings":
		result = settings.LoadCloseSettings(b.deps.StorageDir())
	case "set-close-settings":
		partial, _ := args[0].(map[string]any)
		result = settings.SaveCloseSettings(b.deps.StorageDir(), partial)
		if b.deps.OnCloseSettingsChanged != nil {
			b.deps.OnCloseSettingsChanged()
		}
	case "get-ui-theme":
		if b.deps.GetUiTheme != nil {
			p, e := b.deps.GetUiTheme()
			result = map[string]any{"preference": p, "theme": e}
		}
	case "set-ui-theme":
		if b.deps.SetUiTheme != nil {
			p, e := b.deps.SetUiTheme(argString(args, 0))
			result = map[string]any{"preference": p, "theme": e}
			if b.deps.OnUiThemeChanged != nil {
				b.deps.OnUiThemeChanged(e)
			}
		}
	case "get-screen-security-settings":
		result = system.ScreenSecurityPayload(b.deps.PrivacyPlatform(), b.screenSecurityEnabled())
	case "set-screen-security-enabled":
		result = b.setScreenSecurityEnabled(args[0] == true)
	case "get-memory-usage":
		result = system.GetMemoryUsage()
	case "get-battery-status":
		if st := system.GetBatteryStatus(); st != nil {
			result = st
		} else {
			result = nil
		}
	case "showPathInFolder":
		b.revealPath(argString(args, 0))
		result = nil
	case "open-path":
		if b.deps.OpenPath != nil {
			result = b.deps.OpenPath(argString(args, 0))
		} else {
			result = "Path is not allowed"
		}
	case "pick-file":
		if b.deps.PickFile != nil {
			p, e := b.deps.PickFile()
			if e != nil {
				err = e
			} else {
				result = p
			}
		} else {
			result = nil
		}
	case "pick-directory":
		if b.deps.PickDirectory != nil {
			p, e := b.deps.PickDirectory()
			if e != nil {
				err = e
			} else {
				result = p
			}
		} else {
			result = nil
		}
	case "set-power-save-blocker":
		result = b.setPowerSaveBlocker(args[0] == true)
	case "show-notification":
		data, _ := args[0].(map[string]any)
		title := strField(data, "title")
		body := strField(data, "body")
		silent := data["silent"] == true
		hash := strField(data, "destinationHash")
		if b.deps.NotifyShow != nil {
			b.deps.NotifyShow(title, body, silent, hash)
		}
		result = nil
	case "close-message-notifications":
		var hash *string
		if len(args) > 0 && args[0] != nil {
			s := fmt.Sprint(args[0])
			hash = &s
		}
		if b.deps.NotifyClose != nil {
			result = b.deps.NotifyClose(hash)
		} else {
			result = 0
		}

	// ---- shell page methods (loading/crash/close/prompt) --------------------
	case "backend-probe":
		result = b.backendProbe(argString(args, 0))
	case "backend-config":
		result = b.backendConfig(argString(args, 0))
	case "backend-probe-target":
		result = b.backendProbeTarget()
	case "open-app":
		result = b.openApp(argString(args, 0))
	case "open-external":
		result = b.openExternal(argString(args, 0))
	case "open-window":
		result = b.openWindow(args)
	case "close-window":
		b.closeWindow(argString(args, 0))
		result = nil
	case "window-result":
		result = b.windowResult(window, argString(args, 0), args[1])
	case "download-begin":
		var wid uint
		if window != nil {
			wid = window.ID()
		}
		result = b.downloads.Begin(argString(args, 0), numField(args, 1), wid)
	case "download-chunk":
		result = b.downloads.Chunk(argString(args, 0), argString(args, 1))
	case "download-end":
		result = b.downloads.End(argString(args, 0))
	case "download-abort":
		result = b.downloads.Abort(argString(args, 0))
	case "get-downloads-dir":
		result = b.downloads.Dir()
	case "log":
		if b.deps.Log != nil {
			b.deps.Log(fmt.Sprint(args...))
		}
		result = nil
	case "serial-list-ports":
		result, err = b.serialListPorts()
	case "serial-request-port":
		result, err = b.serialRequestPort(window, argMap(args, 0))
	case "serial-open":
		result, err = b.serialOpen(window, argMap(args, 0))
	case "serial-read":
		result, err = b.serialRead(argMap(args, 0))
	case "serial-write":
		result, err = b.serialWrite(argMap(args, 0))
	case "serial-close":
		result, err = b.serialClose(argMap(args, 0))
	case "serial-set-signals":
		result, err = b.serialSetSignals(argMap(args, 0))
	case "serial-get-signals":
		result, err = b.serialGetSignals(argMap(args, 0))
	case "serial-get-info":
		result, err = b.serialGetInfo(argMap(args, 0))
	case "serial-forget":
		result, err = b.serialForget(argMap(args, 0))
	default:
		err = fmt.Errorf("unknown method %q", method)
	}

	if err != nil {
		b.reply(window, id, false, map[string]any{"error": err.Error()})
		return
	}
	b.reply(window, id, true, result)
}

// ---- helpers ---------------------------------------------------------------

func argString(args []any, i int) string {
	if i >= len(args) || args[i] == nil {
		return ""
	}
	return fmt.Sprint(args[i])
}

func strField(m map[string]any, key string) string {
	if m == nil {
		return ""
	}
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

func argMap(args []any, i int) map[string]any {
	if i >= len(args) || args[i] == nil {
		return nil
	}
	if m, ok := args[i].(map[string]any); ok {
		return m
	}
	return nil
}

func numField(args []any, i int) int64 {
	if i >= len(args) || args[i] == nil {
		return 0
	}
	switch v := args[i].(type) {
	case float64:
		return int64(v)
	case string:
		n, _ := strconv.ParseInt(v, 10, 64)
		return n
	}
	return 0
}

func hasFlag(args []string, flag string) bool {
	for _, a := range args {
		if a == flag || strings.HasPrefix(a, flag+"=") {
			return true
		}
	}
	return false
}

// ---- backend probe ----------------------------------------------------------

// backendProbe performs the status GET in Go (the webview cannot fetch the
// backend cross-origin from the asset origin). TLS verification is relaxed
// only for these loopback probes.
func (b *Bridge) backendProbe(protocol string) map[string]any {
	if protocol != "http" && protocol != "https" {
		protocol = "http"
	}
	url := fmt.Sprintf("%s://127.0.0.1:9337/api/v1/status", protocol)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return map[string]any{"ok": false, "failure": map[string]any{"kind": "network-error"}, "protocol": protocol}
	}
	req.Header.Set("Cache-Control", "no-store")
	resp, err := b.probeClient.Do(req)
	if err != nil {
		kind := "network-error"
		msg := err.Error()
		lower := strings.ToLower(msg)
		switch {
		case strings.Contains(lower, "timeout") || strings.Contains(lower, "deadline"):
			kind = "timeout"
		case strings.Contains(lower, "connection refused"):
			kind = "connection-refused"
		case strings.Contains(lower, "no such host") || strings.Contains(lower, "dns"):
			kind = "dns-error"
		}
		return map[string]any{"ok": false, "failure": map[string]any{"kind": kind, "message": msg}, "protocol": protocol}
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	return map[string]any{
		"ok":         true,
		"httpStatus": resp.StatusCode,
		"body":       string(body),
		"protocol":   protocol,
	}
}

// backendConfig fetches /api/v1/config through the same lenient loopback
// client as backendProbe (used by the loading page for early theme sync).
func (b *Bridge) backendConfig(protocol string) any {
	if protocol != "http" && protocol != "https" {
		protocol = "http"
	}
	url := fmt.Sprintf("%s://127.0.0.1:9337/api/v1/config", protocol)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil
	}
	req.Header.Set("Cache-Control", "no-store")
	resp, err := b.probeClient.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return nil
	}
	var parsed any
	if err := json.Unmarshal(body, &parsed); err != nil {
		return nil
	}
	return parsed
}

func (b *Bridge) backendProbeTarget() map[string]any {
	appURL := "http://127.0.0.1:9337"
	if b.deps.AppURL != nil {
		if u := b.deps.AppURL(); u != "" {
			appURL = u
		}
	}
	return map[string]any{
		"host":     "127.0.0.1",
		"port":     "9337",
		"httpOnly": hasFlag(b.deps.UserProvidedArgs(), "--no-https"),
		"appUrl":   appURL,
	}
}

// openApp navigates the main window to the backend URL (loading page ready).
func (b *Bridge) openApp(rawurl string) map[string]any {
	if !security.IsLocalBackendURL(rawurl) {
		return map[string]any{"ok": false, "error": "refusing to open untrusted URL"}
	}
	win := b.deps.MainWindow()
	if win == nil {
		return map[string]any{"ok": false, "error": "no main window"}
	}
	if b.deps.SetWindowURL != nil {
		b.deps.SetWindowURL(win, rawurl)
	}
	return map[string]any{"ok": true}
}

func (b *Bridge) openExternal(rawurl string) map[string]any {
	safe := security.NormalizeExternalURLForOpen(rawurl)
	if safe == "" {
		return map[string]any{"ok": false}
	}
	if b.deps.OpenExternal != nil {
		b.deps.OpenExternal(safe)
	}
	return map[string]any{"ok": true}
}

// openWindow classifies a window.open request: local popouts become Wails
// child windows; everything else safe goes to the OS browser; the rest is
// denied (matches handleWindowOpenRequest).
func (b *Bridge) openWindow(args []any) map[string]any {
	var spec ChildWindowSpec
	if len(args) > 0 {
		if m, ok := args[0].(map[string]any); ok {
			spec.URL = strField(m, "url")
			spec.Target = strField(m, "target")
			if f, ok := m["width"].(float64); ok {
				spec.Width = int(f)
			}
			if f, ok := m["height"].(float64); ok {
				spec.Height = int(f)
			}
		} else {
			spec.URL = argString(args, 0)
		}
	}
	if spec.Target == "" {
		spec.Target = "_blank"
	}
	url := spec.URL
	if url == "" {
		return map[string]any{"ok": false, "error": "empty url"}
	}
	if security.ShouldOpenInChildWindow(url) {
		if b.deps.OpenChildWindow != nil {
			win, err := b.deps.OpenChildWindow(spec)
			if err != nil {
				return map[string]any{"ok": false, "error": err.Error()}
			}
			if win != nil {
				return map[string]any{"ok": true, "window": win.Name()}
			}
		}
		return map[string]any{"ok": false, "error": "child windows unavailable"}
	}
	// Local backend non-popout URLs stay in the shell: deny.
	if security.IsLocalBackendURL(url) || security.IsTrustedBlobURL(url) {
		return map[string]any{"ok": false, "denied": true}
	}
	if safe := security.NormalizeExternalURLForOpen(url); safe != "" {
		b.openExternal(safe)
	}
	return map[string]any{"ok": true, "external": true}
}

func (b *Bridge) closeWindow(name string) {
	if name == "" || b.deps.CloseChildWindow == nil {
		return
	}
	b.deps.CloseChildWindow(name)
}

func (b *Bridge) windowResult(window application.Window, name string, result any) map[string]any {
	b.mu.Lock()
	pw := b.pendingWindows[name]
	// Only the window the pending entry was registered for may resolve it.
	if pw == nil || window == nil || pw.windowID != window.ID() {
		pw = nil
	} else {
		delete(b.pendingWindows, name)
	}
	b.mu.Unlock()
	if pw != nil {
		data, _ := json.Marshal(result)
		select {
		case pw.ch <- string(data):
		default:
		}
	} else if b.deps.Log != nil {
		b.deps.Log("bridge: dropped window-result for " + name + " (unknown or foreign sender)")
	}
	return map[string]any{"ok": true}
}

// RegisterPendingWindow creates a channel a child window can resolve via
// window-result. Used by prompt/close-dialog/serial-picker windows. The
// entry is bound to window's ID; call after the window exists.
func (b *Bridge) RegisterPendingWindow(name string, window application.Window) chan string {
	ch := make(chan string, 1)
	var windowID uint
	if window != nil {
		windowID = window.ID()
	}
	b.mu.Lock()
	b.pendingWindows[name] = &pendingWindow{ch: ch, windowID: windowID}
	b.mu.Unlock()
	return ch
}

func (b *Bridge) UnregisterPendingWindow(name string) {
	b.mu.Lock()
	delete(b.pendingWindows, name)
	b.mu.Unlock()
}

// ---- crash / recovery --------------------------------------------------------

func (b *Bridge) openBackendCrashReport() map[string]any {
	var lastCrash map[string]any
	if b.deps.Backend != nil {
		lastCrash = b.deps.Backend.GetLastCrash()
	}
	if lastCrash == nil {
		if c := crashreport.LoadCrashReport(b.deps.StorageDir()); c != nil {
			lastCrash = map[string]any{
				"code": c.Code, "signal": c.Signal, "stdout": c.Stdout,
				"stderr": c.Stderr, "at": c.At, "platform": c.Platform, "pid": c.Pid,
			}
		}
	}
	if lastCrash == nil {
		return map[string]any{"ok": false, "error": "No backend crash report is available."}
	}
	if b.deps.ShowCrashPage != nil {
		b.deps.ShowCrashPage(lastCrash)
	}
	return map[string]any{"ok": true}
}

func (b *Bridge) crashRecoveryInfo() map[string]any {
	var stderr, stdout string
	var exitCode *int
	var exitSignal string
	if b.deps.Backend != nil {
		if c := b.deps.Backend.GetLastCrash(); c != nil {
			stderr, _ = c["stderr"].(string)
			stdout, _ = c["stdout"].(string)
			exitSignal, _ = c["signal"].(string)
			if f, ok := c["code"].(float64); ok {
				i := int(f)
				exitCode = &i
			}
		} else if logs := b.deps.Backend.GetJoinedLogs(); logs != nil {
			stderr = logs["stderr"]
			stdout = logs["stdout"]
		}
	}
	rnsDir := ""
	if b.deps.ReticulumConfigDir != nil {
		rnsDir = b.deps.ReticulumConfigDir()
	}
	return crashreport.CrashRecoveryInfo(b.deps.StorageDir(), rnsDir, runtime.GOOS, portableDir(), stderr, stdout, exitCode, exitSignal)
}

func portableDir() string {
	return strings.TrimSpace(os.Getenv("PORTABLE_EXECUTABLE_DIR"))
}

func (b *Bridge) restoreDatabaseBackup(backupPath string) map[string]any {
	if backupPath == "" {
		return map[string]any{"ok": false, "error": "No backup path provided."}
	}
	// Paths under the guard roots pass directly; a path returned by the native
	// backup picker is accepted once via the picker's one-time blessing.
	allowed := b.deps.PathGuard != nil &&
		(b.deps.PathGuard.IsAllowedShellPath(backupPath, true) || b.deps.PathGuard.ConsumeBlessedPath(backupPath))
	if !allowed {
		return map[string]any{"ok": false, "error": "Backup path is not allowed."}
	}
	if _, err := os.Stat(backupPath); err != nil {
		return map[string]any{"ok": false, "error": "Backup file was not found."}
	}
	if b.deps.Backend != nil {
		return b.deps.Backend.RunMaintenanceTask([]string{"--restore-db", backupPath})
	}
	return map[string]any{"ok": false, "error": "backend unavailable"}
}

// revealPath guards then reveals in the file manager.
func (b *Bridge) revealPath(target string) {
	if b.deps.PathGuard == nil || !b.deps.PathGuard.IsAllowedShellPath(target, true) {
		if b.deps.Log != nil {
			b.deps.Log("showPathInFolder denied (path outside allowed directories)")
		}
		return
	}
	if b.deps.RevealPath != nil {
		b.deps.RevealPath(target)
	}
}

// ---- settings / privacy -----------------------------------------------------

func (b *Bridge) screenSecurityEnabled() bool {
	return settings.LoadDesktopPrivacySettings(b.deps.StorageDir()).ScreenSecurityEnabled
}

func (b *Bridge) setScreenSecurityEnabled(enabled bool) any {
	settings.SaveDesktopPrivacySettings(b.deps.StorageDir(), map[string]any{
		"screenSecurityEnabled": enabled,
	})
	if b.deps.SetContentProtection != nil {
		b.deps.SetContentProtection(enabled)
	}
	return system.ScreenSecurityPayload(b.deps.PrivacyPlatform(), enabled)
}

func (b *Bridge) setPowerSaveBlocker(enabled bool) bool {
	if b.deps.PowerSaveBlocker == nil {
		return false
	}
	if enabled {
		return b.deps.PowerSaveBlocker.Start()
	}
	b.deps.PowerSaveBlocker.Stop()
	return false
}

var _ = syscall.SIGTERM
