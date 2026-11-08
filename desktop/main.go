// MeshChatX desktop shell (Wails v3). Hosts the Python backend
// (ReticulumMeshChatX) in a Wails window and bridges renderer IPC through
// application.Options.RawMessageHandler. IPC channel names match the retired
// Electron shell 1:1 for traceability.
package main

import (
	"embed"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/fs"
	"log"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"
	"github.com/wailsapp/wails/v3/pkg/services/notifications"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/appserver"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/backendproc"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/bridge"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/crashreport"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/integrity"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/logger"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/notify"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/paths"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/protocollink"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/security"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/serial"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/settings"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/system"
)

//go:embed all:shell all:assets all:app-version.json
var embedded embed.FS

const (
	appName         = "MeshChatX"
	defaultUniqueID = "com.meshchatx.app"
	wailsVersion    = "3.1.0"
	backendBaseURL  = "127.0.0.1:9337"
)

// singleInstanceID allows tests/CI to run a second shell side-by-side via
// MESHCHATX_UNIQUE_ID; production always uses defaultUniqueID.
func singleInstanceID() string {
	if v := strings.TrimSpace(os.Getenv("MESHCHATX_UNIQUE_ID")); v != "" {
		return v
	}
	return defaultUniqueID
}

var (
	appIconPNG []byte
	appVersion string
	appServer  *appserver.Server
)

func init() {
	appIconPNG, _ = embedded.ReadFile("assets/icon.png")
	if data, err := embedded.ReadFile("app-version.json"); err == nil {
		var v struct {
			Version string `json:"version"`
		}
		if json.Unmarshal(data, &v) == nil {
			appVersion = v.Version
		}
	}
	if appVersion == "" {
		appVersion = "0.0.0"
	}
}

// shellState holds the mutable application state shared by callbacks.
type shellState struct {
	mu            sync.Mutex
	app           *application.App
	mainWindow    application.Window
	childWindows  map[string]application.Window
	pageKind      string // "loading" | "app" | "crash"
	idleTimer     *time.Timer
	idleReleased  bool // main window was parked on /__shell/idle.html
	storageDir    string
	reticulumDir  string
	downloadsDir  string
	userArgs      []string
	headless      bool
	quitting      bool
	plink         *protocollink.Forwarder
	appURL        string
	hardwareAccel bool
	integrity     *integrity.Result
	integrityMu   sync.Mutex // guards integrity (hashing must not hold s.mu)
	backend       *backendproc.Manager
	bridge        *bridge.Bridge
	notifyMgr     *notify.Manager
	powerBlocker  system.PowerSaveBlocker
	pathGuard     *security.PathGuardRoots
	closeGuard    settings.CloseRequestGuard
	tray          *application.SystemTray
	trayMu        sync.Mutex // serializes syncTray (called from several goroutines)
	navMu         sync.Mutex // serializes main-window SetURL+pageKind swaps
	sysLog        *logger.Logger
	serialMgr     *serial.Manager
}

func (s *shellState) setPageKind(kind string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.pageKind = kind
}

func (s *shellState) getPageKind() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.pageKind
}

func (s *shellState) isQuitting() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.quitting
}

func (s *shellState) setQuitting() {
	s.mu.Lock()
	s.quitting = true
	s.mu.Unlock()
}

func main() {
	log.SetFlags(0)
	// Keep the Go shell's heap small; the heavy lifting is WebKit + backend.
	debug.SetGCPercent(50)
	debug.SetMemoryLimit(256 << 20)
	argv := os.Args[1:]

	s := &shellState{childWindows: map[string]application.Window{}}
	s.headless = paths.HasArgvFlag(argv, "--headless")
	s.userArgs = paths.GetUserProvidedArguments(os.Args)

	home, _ := os.UserHomeDir()
	portableDir := strings.TrimSpace(os.Getenv("PORTABLE_EXECUTABLE_DIR"))
	s.storageDir, s.reticulumDir = paths.ResolvePortableStorageRoots(
		os.Args, environMap(), home, runtime.GOOS == "windows", portableDir)
	s.downloadsDir = filepath.Join(home, "Downloads")

	logDir := filepath.Join(s.storageDir, "logs")
	sysLog := logger.New(func() string { return logDir })
	s.sysLog = sysLog
	sysLog.Write("MeshChatX desktop shell starting")

	// GPU/software-rasterizer disable flags must be applied before WebKit init.
	gpuDisabled := system.HardwareAccelerationDisabled(s.storageDir, s.userArgs)
	system.ApplyWebKitGpuEnv(gpuDisabled)
	s.hardwareAccel = !gpuDisabled
	system.ApplyMemoryTuningEnv(s.userArgs)

	// Locate the backend executable (dev override via MESHCHATX_BACKEND_EXE).
	selfPath, err := os.Executable()
	if err != nil {
		selfPath = os.Args[0]
	}
	devRepoRoot := devRepoRootFor(selfPath)
	backendExe, checked := paths.FindBackendExecutable(selfPath, "", devRepoRoot)
	if backendExe == "" && strings.TrimSpace(os.Getenv("MESHCHATX_BACKEND_EXE")) == "" {
		// Checked list is only interesting when no override was given.
		_ = checked
	}

	s.pathGuard = &security.PathGuardRoots{
		StorageDir:            s.storageDir,
		ReticulumConfigDir:    s.reticulumDir,
		DownloadsDir:          s.downloadsDir,
		DocumentsDir:          filepath.Join(home, "Documents"),
		PicturesDir:           filepath.Join(home, "Pictures"),
		TempDir:               os.TempDir(),
		PortableExecutableDir: portableDir,
		UserArgv:              s.userArgs,
		HomeDir:               home,
	}

	// Integrity check on the backend install dir.
	if backendExe != "" {
		res := integrity.VerifyBackendIntegrity(filepath.Dir(backendExe))
		s.integrity = &res
	}

	s.backend = backendproc.NewManager(backendproc.Deps{
		Log:                func(msg string) { sysLog.Write(msg) },
		StorageDir:         func() string { return s.storageDir },
		ReticulumConfigDir: func() string { return s.reticulumDir },
		MainWindowPageKind: func() string { return s.getPageKind() },
		IsQuiting:          s.isQuitting,
		NotifyRenderer: func(channel string, payload any) {
			if s.bridge != nil {
				s.bridge.EmitMain(channel, payload)
			}
		},
		ShowCrashPage:    s.showCrashPage,
		SpoolStdoutToLog: true,
	})
	s.backend.SetUserProvidedArguments(s.backendUserArgs())

	// The app server is the shell's loopback front door: it serves the
	// embedded shell pages under /__shell/ and reverse-proxies everything
	// else to the backend, so loading -> app navigation stays same-origin
	// (one WebKit web process, no retained loading-page process).
	if s.headless {
		runHeadless(s, backendExe, checked, sysLog)
		return
	}
	upstreamScheme := "http"
	if !s.backendStaysHTTP() {
		upstreamScheme = "https"
	}
	shellFS, err := fs.Sub(embedded, "shell")
	if err != nil {
		log.Fatalf("shell assets: %v", err)
	}
	appSrv, err := appserver.Start(shellFS, &url.URL{Scheme: upstreamScheme, Host: backendBaseURL})
	if err != nil {
		log.Fatalf("app server failed to start: %v", err)
	}
	appServer = appSrv
	s.appURL = appSrv.Origin()

	notifSvc := notifications.New()
	app := application.New(application.Options{
		Name:        appName,
		Description: "Reticulum MeshChatX desktop shell",
		Icon:        appIconPNG,
		Assets: application.AssetOptions{
			Handler: application.BundledAssetFileServer(embedded),
		},
		RawMessageHandler: func(window application.Window, message string, originInfo *application.OriginInfo) {
			if s.bridge != nil {
				s.bridge.Handle(window, message, originInfo)
			}
		},
		SingleInstance: &application.SingleInstanceOptions{
			UniqueID: singleInstanceID(),
			OnSecondInstanceLaunch: func(data application.SecondInstanceData) {
				s.onSecondInstance(data)
			},
		},
		// The shell lives in the tray when its window is hidden; never let
		// the last-window-closed path kill the app (macOS already defaults
		// ApplicationShouldTerminateAfterLastWindowClosed to false).
		Linux:    application.LinuxOptions{DisableQuitOnLastWindowClosed: true},
		Windows:  application.WindowsOptions{DisableQuitOnLastWindowClosed: true},
		Services: []application.Service{application.NewService(notifSvc)},
		OnShutdown: func() {
			s.shutdownBackend(sysLog)
		},
	})
	s.app = app
	app.Event.OnApplicationEvent(events.Common.ApplicationLaunchedWithUrl, func(e *application.ApplicationEvent) {
		s.showMainWindow()
		s.handleProtocolURL(e.Context().URL())
	})

	// Main window starts on the app-server loading page; the page probes the
	// backend and asks Go to navigate to the app URL when ready. Both live on
	// the same loopback origin so WebKit keeps a single web process.
	_, effectiveTheme := s.uiTheme()
	winW, winH := 1500, 800
	if scr := app.Screen.GetPrimary(); scr != nil && scr.WorkArea.Width > 0 && scr.WorkArea.Height > 0 {
		winW = min(winW, scr.WorkArea.Width*9/10)
		winH = min(winH, scr.WorkArea.Height*9/10)
	}
	win := app.Window.NewWithOptions(application.WebviewWindowOptions{
		Name:             "main",
		Title:            appName,
		Width:            winW,
		Height:           winH,
		InitialPosition:  application.WindowCentered,
		MinWidth:         900,
		MinHeight:        600,
		URL:              appSrv.Origin() + "/__shell/loading.html?theme=" + effectiveTheme,
		BackgroundColour: themeColour(effectiveTheme),
		Permissions: map[application.PermissionType]application.Permission{
			application.PermissionMicrophone: application.PermissionAllow,
			application.PermissionCamera:     application.PermissionAllow,
		},
	})
	s.armBridgeToken(win)
	s.mainWindow = win
	s.setPageKind("loading")
	win.RegisterHook(events.Common.WindowClosing, func(e *application.WindowEvent) {
		e.Cancel()
		go s.handleWindowClose()
	})

	// System tray driven by close settings.
	s.syncTray()

	// Notifications service.
	s.notifyMgr = notify.NewManager(notifSvc)
	s.notifyMgr.SetOnClick(func() { s.showMainWindow() })
	if notifSvc != nil {
		notifSvc.OnNotificationResponse(func(result notifications.NotificationResult) {
			if result.Error == nil {
				s.showMainWindow()
			}
		})
	}

	s.powerBlocker = system.NewPowerSaveBlocker()

	// Wire the bridge.
	s.serialMgr = serial.NewManager(serial.Deps{})
	s.bridge = bridge.New(s.bridgeDeps())
	s.plink = protocollink.New(s.getPageKind, func(u string) {
		if s.bridge != nil {
			s.bridge.EmitMain("open-protocol-link", map[string]any{"url": u})
		}
	})

	// Start the backend, then decide the app URL (plain HTTP loopback or the
	// in-process TLS bridge on :9338).
	s.startBackendAndNavigate(backendExe, checked, sysLog)

	// Flush a pending protocol link once the app page is showing.
	if u := paths.FindProtocolUrlArg(os.Args); u != "" {
		s.plink.Offer(u)
	}
	go s.flushProtocolLinkWhenReady()

	if err := app.Run(); err != nil {
		log.Fatal(err)
	}
}

// ---- backend lifecycle ------------------------------------------------------

func (s *shellState) backendUserArgs() []string {
	args := append([]string(nil), s.userArgs...)
	// Loopback backend without user certs runs plain HTTP; the shell then
	// talks to http://127.0.0.1:9337 directly (TLS bridge only when needed).
	if s.backendStaysHTTP() && !paths.HasArgvFlag(args, "--no-https") {
		args = append(args, "--no-https")
	}
	return args
}

func (s *shellState) backendHostIsLoopback() bool {
	host := strings.TrimSpace(os.Getenv("MESHCHAT_HOST"))
	if host == "" {
		if h := paths.ParseArgvFlag(s.userArgs, "--host"); h != "" {
			host = h
		}
	}
	if host == "" {
		return true
	}
	host = strings.Trim(host, "[]")
	if i := strings.LastIndex(host, ":"); i >= 0 && !strings.Contains(host[i+1:], "]") {
		// strip port unless IPv6 literal
		if strings.Count(host, ":") == 1 {
			host = host[:i]
		}
	}
	return host == "127.0.0.1" || host == "localhost" || host == "::1"
}

func (s *shellState) backendStaysHTTP() bool {
	return s.backendHostIsLoopback() &&
		!paths.HasArgvFlag(s.userArgs, "--ssl-cert") &&
		!paths.HasArgvFlag(s.userArgs, "--ssl-key") &&
		!paths.HasArgvFlag(s.userArgs, "--https")
}

func (s *shellState) startBackendAndNavigate(backendExe string, checked []string, sysLog *logger.Logger) {
	if backendExe == "" {
		sysLog.Write("Backend executable not found; checked: " + strings.Join(checked, ", "))
		s.showStartupFailure("Backend executable not found", strings.Join(checked, "\n"))
		return
	}
	go func() {
		_, err := s.backend.SpawnBackend(backendExe, s.integrity)
		if err != nil {
			sysLog.Write("Backend spawn failed: " + err.Error())
			s.showStartupFailure("Backend failed to start", err.Error())
		}
	}()
}

func (s *shellState) showStartupFailure(title, detail string) {
	// Navigate the loading page into its failure state via crash page.
	s.showCrashPage(map[string]any{
		"code":    nil,
		"signal":  "",
		"stdout":  "",
		"stderr":  detail,
		"startup": true,
		"title":   title,
	})
}

func (s *shellState) shutdownBackend(sysLog *logger.Logger) {
	s.setQuitting()
	if s.powerBlocker != nil {
		s.powerBlocker.Stop()
	}
	if s.serialMgr != nil {
		s.serialMgr.CloseAll()
	}
	if s.backend == nil {
		return
	}
	if cmd := s.backend.ChildProcess(); cmd != nil && cmd.Process != nil {
		s.backend.KillChild(syscall.SIGTERM)
		done := make(chan struct{})
		go func() {
			_ = cmd.Wait()
			close(done)
		}()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			s.backend.KillChild(syscall.SIGKILL)
		}
	}
	if appServer != nil {
		appServer.Stop()
	}
	sysLog.Write("MeshChatX desktop shell exiting")
}

func (s *shellState) relaunch(extraArgs ...string) {
	s.setQuitting()
	exe, err := os.Executable()
	if err != nil {
		return
	}
	if appimage := strings.TrimSpace(os.Getenv("APPIMAGE")); appimage != "" {
		exe = appimage
	}
	args := append(append([]string(nil), s.userArgs...), extraArgs...)
	cmd := exec.Command(exe, args...)
	cmd.Dir, _ = os.Getwd()
	cmd.Stdout = nil
	cmd.Stderr = nil
	cmd.Stdin = nil
	if err := cmd.Start(); err != nil {
		return
	}
	// Detach so the child survives this process.
	if runtime.GOOS != "windows" {
		_ = cmd.Process.Release()
	}
	s.shutdownBackend(logger.New(func() string { return filepath.Join(s.storageDir, "logs") }))
	if s.app != nil {
		s.app.Quit()
	}
}

// ---- close behavior ---------------------------------------------------------

func (s *shellState) handleWindowClose() {
	if s.isQuitting() || !s.closeGuard.TryEnter() {
		return
	}
	defer s.closeGuard.Leave()

	settingsRaw := settings.LoadCloseSettings(s.storageDir)
	action := settings.ResolveCloseAction(settingsRaw)
	win := s.mainWindow

	switch action {
	case "quit":
		s.quitApp()
	case "background":
		win.Hide()
		s.onMainWindowHidden()
	case "minimize":
		win.Minimise()
	case "ask":
		result, remember, ok := s.askCloseDialog()
		if !ok {
			return // cancelled: keep window open
		}
		switch result {
		case "quit":
			s.quitApp()
		case "minimize":
			win.Minimise()
		case "background":
			win.Hide()
			s.onMainWindowHidden()
		}
		if partial := settings.RememberedCloseSettings(result, remember); partial != nil {
			settings.SaveCloseSettings(s.storageDir, partial)
			s.syncTray()
		}
	}
}

// askCloseDialog opens close-dialog.html as a small modal-ish child window
// and waits for its window-result message.
func (s *shellState) askCloseDialog() (action string, remember bool, ok bool) {
	_, effective := s.uiTheme()
	name := "close-dialog"
	w := s.app.Window.NewWithOptions(application.WebviewWindowOptions{
		Name:             name,
		Title:            "Close MeshChatX?",
		Width:            460,
		Height:           320,
		DisableResize:    true,
		URL:              "/close-dialog.html?theme=" + effective + "&tray=" + map[bool]string{true: "1", false: "0"}[settings.LoadCloseSettings(s.storageDir).TrayEnabled],
		BackgroundColour: themeColour(effective),
		Hidden:           false,
		AlwaysOnTop:      true,
	})
	ch := s.bridge.RegisterPendingWindow(name, w)
	defer s.bridge.UnregisterPendingWindow(name)
	s.armBridgeToken(w)
	s.mainWindow.AttachModal(w)
	s.mu.Lock()
	s.childWindows[name] = w
	s.mu.Unlock()
	defer func() {
		s.mu.Lock()
		delete(s.childWindows, name)
		s.mu.Unlock()
		w.Close()
	}()

	select {
	case raw := <-ch:
		var res struct {
			Action   string `json:"action"`
			Remember bool   `json:"remember"`
		}
		if err := json.Unmarshal([]byte(raw), &res); err != nil {
			return "", false, false
		}
		if res.Action == "cancel" || res.Action == "" {
			return "", false, false
		}
		return res.Action, res.Remember, true
	case <-time.After(2 * time.Minute):
		return "", false, false
	}
}

func (s *shellState) quitApp() {
	if s.isQuitting() {
		return
	}
	s.setQuitting()
	if s.app != nil {
		s.app.Quit()
	}
}

// ---- tray -------------------------------------------------------------------

func (s *shellState) syncTray() {
	s.trayMu.Lock()
	defer s.trayMu.Unlock()
	if s.app == nil {
		return
	}
	want := settings.LoadCloseSettings(s.storageDir).TrayEnabled
	if want && s.tray == nil {
		tray := s.app.SystemTray.New()
		if len(appIconPNG) > 0 {
			tray.SetIcon(appIconPNG)
		}
		tray.SetTooltip(appName)
		tray.OnClick(func() { s.toggleMainWindow() })
		menu := s.app.NewMenu()
		show := menu.Add("Show App")
		show.OnClick(func(*application.Context) { s.showMainWindow() })
		menu.AddSeparator()
		quit := menu.Add("Quit")
		quit.OnClick(func(*application.Context) { s.quitApp() })
		tray.SetMenu(menu)
		s.tray = tray
	} else if !want && s.tray != nil {
		s.tray.Destroy()
		s.tray = nil
	}
}

func (s *shellState) toggleMainWindow() {
	win := s.mainWindow
	if win == nil {
		return
	}
	if win.IsVisible() {
		win.Hide()
		s.onMainWindowHidden()
	} else {
		s.showMainWindow()
	}
}

// idleReleaseDelay is how long the main window must stay hidden to the tray
// before its heavy app page is swapped for the tiny idle page.
const idleReleaseDelay = 10 * time.Minute

// onMainWindowHidden arms the idle-release timer. Only fires while the
// window remains hidden (never on minimise/visible) and only on the app
// page — loading/crash pages are already tiny.
func (s *shellState) onMainWindowHidden() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.idleTimer != nil || s.idleReleased || appServer == nil || s.pageKind != "app" {
		return
	}
	s.idleTimer = time.AfterFunc(idleReleaseDelay, func() {
		// navMu serializes this swap against showMainWindow's restore: without
		// it a concurrent show could interleave SetURL calls and leave a
		// visible window parked on idle.html.
		s.navMu.Lock()
		defer s.navMu.Unlock()
		if s.mainWindow == nil || s.mainWindow.IsVisible() {
			s.mu.Lock()
			s.idleTimer = nil
			s.mu.Unlock()
			return
		}
		s.mu.Lock()
		if s.pageKind != "app" {
			s.idleTimer = nil
			s.mu.Unlock()
			return
		}
		s.idleTimer = nil
		s.idleReleased = true
		s.mu.Unlock()
		s.mainWindow.SetURL(appServer.Origin() + "/__shell/idle.html")
		s.setPageKind("other")
	})
}

// armBridgeToken registers the per-page-load capability token rotation for a
// window (main frame only via ExecJS).
func (s *shellState) armBridgeToken(w application.Window) {
	// Per-OS "page finished loading" events (no common one exists).
	for _, ev := range []events.WindowEventType{
		events.Linux.WindowLoadFinished,
		events.Mac.WebViewDidFinishNavigation,
		events.Windows.WebViewNavigationCompleted,
	} {
		ev := ev
		w.RegisterHook(ev, func(e *application.WindowEvent) {
			if s.bridge != nil {
				s.bridge.RotateToken(w)
			}
			if w == s.mainWindow && s.getPageKind() == "app" {
				go s.flushProtocolLinkWhenReady()
			}
		})
	}
	w.RegisterHook(events.Common.WindowClosing, func(e *application.WindowEvent) {
		// The main window's close is always intercepted (hide-to-tray /
		// close dialog), so invalidating here would brick the bridge for a
		// page that stays alive. Only real child-window closes invalidate.
		if w == s.mainWindow {
			return
		}
		// Popouts/dialogs closed via their own close button never pass
		// through closeChildWindow; drop the map entry here so it can't leak.
		s.mu.Lock()
		for name, cw := range s.childWindows {
			if cw == w {
				delete(s.childWindows, name)
				break
			}
		}
		s.mu.Unlock()
		if s.bridge != nil {
			s.bridge.InvalidateWindow(w)
		}
	})
}

func (s *shellState) showMainWindow() {
	win := s.mainWindow
	if win == nil {
		return
	}
	s.navMu.Lock()
	s.mu.Lock()
	if s.idleTimer != nil {
		s.idleTimer.Stop()
		s.idleTimer = nil
	}
	released := s.idleReleased
	s.idleReleased = false
	s.mu.Unlock()
	if released && appServer != nil {
		win.SetURL(s.appURL + "/?nocache=" + fmt.Sprint(time.Now().UnixMilli()))
		s.setPageKind("app")
	}
	s.navMu.Unlock()
	win.Show()
	win.Focus()
	win.UnMinimise()
}

// ---- protocol links / second instance ---------------------------------------

func (s *shellState) handleProtocolURL(raw string) {
	// ApplicationLaunchedWithUrl delivers whatever URL the OS hands us; only
	// the registered deep-link schemes may reach the app page.
	if raw == "" || !paths.IsProtocolURL(raw) {
		return
	}
	if s.plink.Offer(raw) {
		go s.flushProtocolLinkWhenReady()
	}
}

func (s *shellState) onSecondInstance(data application.SecondInstanceData) {
	s.showMainWindow()
	if u := paths.FindProtocolUrlArg(data.Args); u != "" {
		s.handleProtocolURL(u)
	}
}

func (s *shellState) flushProtocolLinkWhenReady() {
	s.plink.Flush(500*time.Millisecond, 240)
}

// ---- dialogs / pickers --------------------------------------------------------

func (s *shellState) uiTheme() (pref, effective string) {
	pref = settings.LoadUiThemePreference(s.storageDir)
	effective = settings.ResolveEffectiveUiTheme(pref, s.app != nil && s.app.Env.IsDarkMode())
	return pref, effective
}

func themeColour(theme string) application.RGBA {
	if theme == "dark" {
		return application.NewRGBA(24, 24, 27, 255)
	}
	return application.NewRGBA(245, 245, 245, 255)
}

func (s *shellState) showMessageDialog(kind, title, message string) int {
	if s.app == nil {
		return 0
	}
	var dlg *application.MessageDialog
	switch kind {
	case "warning":
		dlg = s.app.Dialog.Warning()
	case "error":
		dlg = s.app.Dialog.Error()
	default:
		dlg = s.app.Dialog.Info()
	}
	if title != "" {
		dlg.SetTitle(title)
	}
	dlg.SetMessage(message)
	result := 0
	okBtn := dlg.AddButton("OK")
	okBtn.IsDefault = true
	okBtn.OnClick(func() { result = 1 })
	dlg.SetDefaultButton(okBtn)
	dlg.Show()
	return result
}

func (s *shellState) confirmDialog(message string) bool {
	if s.app == nil {
		return false
	}
	dlg := s.app.Dialog.Question()
	dlg.SetTitle(appName)
	dlg.SetMessage(message)
	result := false
	okBtn := dlg.AddButton("OK")
	okBtn.IsDefault = true
	okBtn.OnClick(func() { result = true })
	dlg.SetDefaultButton(okBtn)
	cancelBtn := dlg.AddButton("Cancel")
	cancelBtn.IsCancel = true
	cancelBtn.OnClick(func() { result = false })
	dlg.SetCancelButton(cancelBtn)
	dlg.Show()
	return result
}

func (s *shellState) promptDialog(message, def string) (string, bool) {
	name := "prompt-dialog"
	_, effective := s.uiTheme()
	w := s.app.Window.NewWithOptions(application.WebviewWindowOptions{
		Name:             name,
		Title:            appName,
		Width:            520,
		Height:           240,
		DisableResize:    true,
		URL:              "/prompt.html?theme=" + effective + "&message=" + urlQueryEscape(message) + "&default=" + urlQueryEscape(def),
		BackgroundColour: themeColour(effective),
		AlwaysOnTop:      true,
	})
	ch := s.bridge.RegisterPendingWindow(name, w)
	defer s.bridge.UnregisterPendingWindow(name)
	s.armBridgeToken(w)
	s.mainWindow.AttachModal(w)
	s.mu.Lock()
	s.childWindows[name] = w
	s.mu.Unlock()
	defer func() {
		s.mu.Lock()
		delete(s.childWindows, name)
		s.mu.Unlock()
		w.Close()
	}()
	select {
	case raw := <-ch:
		var res struct {
			Value *string `json:"value"`
		}
		if err := json.Unmarshal([]byte(raw), &res); err != nil || res.Value == nil {
			return "", false
		}
		return *res.Value, true
	case <-time.After(2 * time.Minute):
		return "", false
	}
}

// pickSerialPort opens the serial-picker.html modal and resolves with the
// chosen port's JSON ({"path": ...}) or "" on cancel/timeout.
func (s *shellState) pickSerialPort(filtersJSON string) (string, bool) {
	name := "serial-picker"
	_, effective := s.uiTheme()
	w := s.app.Window.NewWithOptions(application.WebviewWindowOptions{
		Name:             name,
		Title:            "Select serial port",
		Width:            440,
		Height:           380,
		DisableResize:    true,
		URL:              "/serial-picker.html?theme=" + effective + "&filters=" + urlQueryEscape(filtersJSON),
		BackgroundColour: themeColour(effective),
		AlwaysOnTop:      true,
	})
	ch := s.bridge.RegisterPendingWindow(name, w)
	defer s.bridge.UnregisterPendingWindow(name)
	s.armBridgeToken(w)
	s.mainWindow.AttachModal(w)
	s.mu.Lock()
	s.childWindows[name] = w
	s.mu.Unlock()
	defer func() {
		s.mu.Lock()
		delete(s.childWindows, name)
		s.mu.Unlock()
		w.Close()
	}()
	select {
	case raw := <-ch:
		return raw, true
	case <-time.After(5 * time.Minute):
		return "", false
	}
}

func urlQueryEscape(s string) string {
	return strings.NewReplacer("%", "%25", "&", "%26", "=", "%3D", "#", "%23", " ", "%20", "+", "%2B").Replace(s)
}

func (s *shellState) pickFile() (string, error) {
	dlg := s.app.Dialog.OpenFile()
	dlg.SetTitle("Choose file")
	return dlg.PromptForSingleSelection()
}

func (s *shellState) pickDirectory() (string, error) {
	dlg := s.app.Dialog.OpenFile()
	dlg.SetTitle("Choose folder")
	dlg.CanChooseFiles(false)
	dlg.CanChooseDirectories(true)
	return dlg.PromptForSingleSelection()
}

func (s *shellState) pickDatabaseBackup() (string, error) {
	dlg := s.app.Dialog.OpenFile()
	dlg.SetTitle("Choose database backup")
	dlg.AddFilter("Zip archives", "*.zip")
	if s.storageDir != "" {
		dlg.SetDirectory(filepath.Join(s.storageDir, "backups"))
	}
	p, err := dlg.PromptForSingleSelection()
	if err == nil && p != "" && s.pathGuard != nil {
		// The picker can return paths outside the guard roots (~/Desktop,
		// ~/, other volumes); bless this exact pick once so restore accepts it.
		s.pathGuard.BlessPath(p)
	}
	return p, err
}

func (s *shellState) revealPath(target string) {
	if target == "" {
		return
	}
	abs, err := filepath.Abs(target)
	if err != nil {
		return
	}
	info, err := os.Stat(abs)
	if err != nil {
		return
	}
	dir := abs
	if !info.IsDir() {
		dir = filepath.Dir(abs)
	}
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		if info.IsDir() {
			cmd = exec.Command("explorer", abs)
		} else {
			cmd = exec.Command("explorer", "/select,", abs)
		}
	case "darwin":
		if info.IsDir() {
			cmd = exec.Command("open", abs)
		} else {
			cmd = exec.Command("open", "-R", abs)
		}
	default:
		cmd = exec.Command("xdg-open", dir)
	}
	_ = cmd.Start()
}

func (s *shellState) openPath(target string) string {
	if target == "" || s.pathGuard == nil || !s.pathGuard.IsAllowedShellPath(target, false) {
		return "Path is not allowed"
	}
	abs, err := filepath.Abs(target)
	if err != nil {
		return "Path is not allowed"
	}
	if _, err := os.Stat(abs); err != nil {
		return "Path not found"
	}
	if err := s.app.Browser.OpenFile(abs); err != nil {
		return err.Error()
	}
	return ""
}

func (s *shellState) openExternal(rawurl string) bool {
	safe := security.NormalizeExternalURLForOpen(rawurl)
	if safe == "" || s.app == nil {
		return false
	}
	return s.app.Browser.OpenURL(safe) == nil
}

// ---- child windows ------------------------------------------------------------

func (s *shellState) openChildWindow(spec bridge.ChildWindowSpec) (application.Window, error) {
	if !security.IsTrustedShellPageURL(spec.URL) && !security.IsLocalBackendURL(spec.URL) {
		return nil, fmt.Errorf("window URL is not trusted")
	}
	width, height := spec.Width, spec.Height
	if width <= 0 {
		width = 800
	}
	if height <= 0 {
		height = 600
	}
	if width > 4000 {
		width = 4000
	}
	if height > 4000 {
		height = 4000
	}
	name := fmt.Sprintf("child-%d", time.Now().UnixNano())
	w := s.app.Window.NewWithOptions(application.WebviewWindowOptions{
		Name:      name,
		Title:     appName,
		Width:     width,
		Height:    height,
		MinWidth:  320,
		MinHeight: 240,
		URL:       spec.URL,
		Permissions: map[application.PermissionType]application.Permission{
			application.PermissionMicrophone: application.PermissionAllow,
			application.PermissionCamera:     application.PermissionAllow,
		},
	})
	s.armBridgeToken(w)
	s.mu.Lock()
	s.childWindows[name] = w
	s.mu.Unlock()
	return w, nil
}

func (s *shellState) closeChildWindow(name string) {
	s.mu.Lock()
	w := s.childWindows[name]
	delete(s.childWindows, name)
	s.mu.Unlock()
	if w != nil {
		w.Close()
	}
}

func (s *shellState) allWindows() []application.Window {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]application.Window, 0, len(s.childWindows)+1)
	if s.mainWindow != nil {
		out = append(out, s.mainWindow)
	}
	for _, w := range s.childWindows {
		out = append(out, w)
	}
	return out
}

// ---- theme / privacy ------------------------------------------------------------

func (s *shellState) getUiTheme() (pref, effective string) {
	return s.uiTheme()
}

func (s *shellState) setUiTheme(pref string) (saved, effective string) {
	saved = settings.SaveUiThemePreference(s.storageDir, pref)
	effective = settings.ResolveEffectiveUiTheme(saved, s.app != nil && s.app.Env.IsDarkMode())
	colour := themeColour(effective)
	for _, w := range s.allWindows() {
		w.SetBackgroundColour(colour)
	}
	return saved, effective
}

func (s *shellState) setContentProtection(enabled bool) {
	for _, w := range s.allWindows() {
		w.SetContentProtection(enabled)
	}
}

// ---- crash page -----------------------------------------------------------------

func (s *shellState) showCrashPage(crash map[string]any) {
	if s.mainWindow == nil || s.app == nil {
		return
	}
	_, effective := s.uiTheme()
	logPath := crashreport.GetBackendLogPath(s.storageDir)
	crashPath := crashreport.GetCrashReportPath(s.storageDir)

	str := func(key string) string {
		if v, ok := crash[key].(string); ok {
			return v
		}
		return ""
	}
	code := ""
	switch v := crash["code"].(type) {
	case float64:
		code = fmt.Sprintf("%d", int(v))
	case int:
		code = fmt.Sprintf("%d", v)
	case string:
		code = v
	}
	if code == "" {
		code = str("signal")
	}
	enc := func(v string) string { return base64.StdEncoding.EncodeToString([]byte(v)) }

	q := "?theme=" + effective +
		"&code=" + urlQueryEscape(code) +
		"&logPath=" + urlQueryEscape(logPath) +
		"&crashReportPath=" + urlQueryEscape(crashPath) +
		"&stdout=" + urlQueryEscape(enc(str("stdout"))) +
		"&stderr=" + urlQueryEscape(enc(str("stderr")))
	crashURL := "/__shell/crash.html" + q
	if appServer != nil {
		crashURL = appServer.Origin() + crashURL
	}
	s.navMu.Lock()
	s.mainWindow.SetURL(crashURL)
	s.setPageKind("crash")
	s.navMu.Unlock()
}

// ---- bridge deps ------------------------------------------------------------------

func (s *shellState) bridgeDeps() bridge.Deps {
	return bridge.Deps{
		MainWindow:         func() application.Window { return s.mainWindow },
		WindowByName:       func(name string) application.Window { s.mu.Lock(); defer s.mu.Unlock(); return s.childWindows[name] },
		AllWindows:         s.allWindows,
		PageKind:           s.getPageKind,
		ShowMainWindow:     s.showMainWindow,
		FocusMainWindow:    s.showMainWindow,
		StorageDir:         func() string { return s.storageDir },
		DownloadsDir:       func() string { return s.downloadsDir },
		ReticulumConfigDir: func() string { return s.reticulumDir },
		UserProvidedArgs:   func() []string { return s.userArgs },
		IntegrityStatus: func() *integrity.Result {
			s.integrityMu.Lock()
			defer s.integrityMu.Unlock()
			if s.integrity == nil {
				res := integrity.VerifyBackendIntegrity("")
				s.integrity = &res
			}
			return s.integrity
		},
		SetIntegrityStatus: func(r integrity.Result) {
			s.integrityMu.Lock()
			s.integrity = &r
			s.integrityMu.Unlock()
		},
		Backend:         s.backend,
		AppVersion:      func() string { return appVersion },
		WailsVersion:    func() string { return wailsVersion },
		IsHardwareAccel: func() bool { return s.hardwareAccel },
		AppURL:          func() string { return s.appURL },
		WebViewKind: func() string {
			switch runtime.GOOS {
			case "windows":
				return "webview2"
			case "darwin":
				return "webkit"
			default:
				return "webkitgtk-6.0"
			}
		},
		Quit:               s.quitApp,
		Relaunch:           s.relaunch,
		ApplyUpdateAndExit: s.applyUpdateAndExit,
		OpenExternal:       s.openExternal,
		OpenChildWindow:    s.openChildWindow,
		CloseChildWindow:   s.closeChildWindow,
		NotifyShow: func(title, body string, silent bool, hash string) {
			if s.notifyMgr != nil {
				s.notifyMgr.Show(title, body, silent, hash)
			}
		},
		NotifyClose: func(hash *string) int {
			if s.notifyMgr == nil {
				return 0
			}
			return s.notifyMgr.CloseMessageNotifications(hash)
		},
		PowerSaveBlocker:     s.powerBlocker,
		PickFile:             s.pickFile,
		PickDirectory:        s.pickDirectory,
		PickDatabaseBackup:   s.pickDatabaseBackup,
		RevealPath:           s.revealPath,
		OpenPath:             s.openPath,
		PathGuard:            s.pathGuard,
		ShowMessage:          s.showMessageDialog,
		ConfirmDialog:        s.confirmDialog,
		PromptDialog:         s.promptDialog,
		SetContentProtection: s.setContentProtection,
		PrivacyPlatform:      func() string { return runtime.GOOS },
		SetUiTheme:           s.setUiTheme,
		GetUiTheme:           s.getUiTheme,
		IsHeadless:           func() bool { return s.headless },
		SetWindowURL: func(win application.Window, rawurl string) {
			if win == s.mainWindow {
				s.navMu.Lock()
				win.SetURL(rawurl)
				if security.IsAppPageURL(rawurl) {
					s.setPageKind("app")
				}
				s.navMu.Unlock()
				return
			}
			win.SetURL(rawurl)
		},
		ShowCrashPage:          s.showCrashPage,
		OnCloseSettingsChanged: func() { s.syncTray() },
		OnUiThemeChanged:       func(effective string) { s.setUiThemeEffective(effective) },
		Serial:                 s.serialMgr,
		PickSerialPort:         s.pickSerialPort,
		Log: func(msg string) {
			if s.sysLog != nil {
				s.sysLog.Write(msg)
			}
		},
	}
}

func (s *shellState) setUiThemeEffective(effective string) {
	colour := themeColour(effective)
	for _, w := range s.allWindows() {
		w.SetBackgroundColour(colour)
	}
}

func (s *shellState) applyUpdateAndExit() {
	// update-apply already persisted; relaunch picks up the new backend.
	s.relaunch()
}

// ---- misc ----------------------------------------------------------------------

func environMap() map[string]string {
	env := map[string]string{}
	for _, kv := range os.Environ() {
		if i := strings.Index(kv, "="); i > 0 {
			env[kv[:i]] = kv[i+1:]
		}
	}
	return env
}

func devRepoRootFor(selfPath string) string {
	// <repo>/desktop/bin/<exe> or <repo>/desktop/<exe> → <repo>
	dir := filepath.Dir(selfPath)
	for _, candidate := range []string{
		filepath.Join(dir, "..", ".."),
		filepath.Join(dir, ".."),
	} {
		root := filepath.Clean(candidate)
		if st, err := os.Stat(filepath.Join(root, "meshchatx")); err == nil && st.IsDir() {
			if _, err := os.Stat(filepath.Join(root, "desktop", "go.mod")); err == nil {
				return root
			}
		}
	}
	return ""
}

func runHeadless(s *shellState, backendExe string, checked []string, sysLog *logger.Logger) {
	if backendExe == "" {
		fmt.Fprintln(os.Stderr, "backend executable not found; checked:")
		for _, c := range checked {
			fmt.Fprintln(os.Stderr, "  "+c)
		}
		os.Exit(1)
	}
	if _, err := s.backend.SpawnBackend(backendExe, s.integrity); err != nil {
		fmt.Fprintln(os.Stderr, "backend spawn failed:", err)
		os.Exit(1)
	}
	sysLog.Write("headless backend running")
	sigCh := make(chan os.Signal, 2)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh
	s.shutdownBackend(sysLog)
}
