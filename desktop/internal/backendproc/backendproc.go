// Package backendproc ports electron/backendProcess.js and
// backendProcessOrphans.js: spawn/monitor/restart the Python backend, capture
// crash state, run maintenance tasks and reap orphan backends.
package backendproc

import (
	"bufio"
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/crashreport"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/integrity"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/paths"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/system"
)

const LogLineCap = 200
const BackendImageName = "ReticulumMeshChatX"

// maintenanceTaskTimeout bounds RunMaintenanceTask; restores of large
// databases are the slowest legitimate task. A var so tests can shrink it.
var maintenanceTaskTimeout = 10 * time.Minute

type RuntimeState struct {
	Started        bool   `json:"started"`
	Running        bool   `json:"running"`
	Pid            *int   `json:"pid"`
	LastExitCode   *int   `json:"lastExitCode"`
	LastExitSignal string `json:"lastExitSignal"`
	LastError      string `json:"lastError"`
	LastEventAt    *int64 `json:"lastEventAt"`
}

func InitialRuntimeState() RuntimeState {
	return RuntimeState{LastExitSignal: ""}
}

// Callbacks the manager needs from the app shell.
type Deps struct {
	Log                func(msg string)
	StorageDir         func() string
	ReticulumConfigDir func() string
	MainWindowPageKind func() string
	IsQuiting          func() bool
	NotifyRenderer     func(channel string, payload any)
	ShowCrashPage      func(crash map[string]any)
	SpoolStdoutToLog   bool // mirror backend stdout/stderr chunks into log()
}

type Manager struct {
	deps Deps

	mu                  sync.Mutex
	spawnMu             sync.Mutex // serializes SpawnBackend check+sweep+spawn+register
	child               *exec.Cmd
	childDone           chan struct{}
	childExitCode       *int
	childExitSignal     string
	maintenance         *exec.Cmd
	maintenanceDone     chan struct{}
	maintenanceExitCode *int

	runtimeState RuntimeState
	logBuffers   map[string][]string
	lastCrash    map[string]any
	resolvedExe  string
	userArgs     []string
	integrity    *integrity.Result
}

func NewManager(deps Deps) *Manager {
	m := &Manager{
		deps:       deps,
		logBuffers: map[string][]string{"stdout": {}, "stderr": {}},
	}
	m.runtimeState = InitialRuntimeState()
	// Hydrate persisted crash report.
	if c := crashreport.LoadCrashReport(deps.StorageDir()); c != nil {
		m.lastCrash = crashToMap(c)
	}
	return m
}

func crashToMap(c *crashreport.Crash) map[string]any {
	return map[string]any{
		"code": c.Code, "signal": c.Signal, "stdout": c.Stdout, "stderr": c.Stderr,
		"at": c.At, "platform": c.Platform, "pid": c.Pid,
	}
}

func (m *Manager) SetUserProvidedArguments(args []string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.userArgs = append([]string(nil), args...)
}

func (m *Manager) ResolveExecutablePath(find func() string) string {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.resolvedExe = find()
	return m.resolvedExe
}

func (m *Manager) GetResolvedExecutablePath() string {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.resolvedExe
}

// procExited reports whether the Wait goroutine has finished (done is closed
// after cmd.Wait() returns). Reading cmd.ProcessState directly races with
// Wait, so liveness is tracked through these channels instead.
func procExited(done chan struct{}) bool {
	if done == nil {
		return false
	}
	select {
	case <-done:
		return true
	default:
		return false
	}
}

func procAlive(cmd *exec.Cmd, done chan struct{}) bool {
	return cmd != nil && cmd.Process != nil && !procExited(done)
}

func (m *Manager) isRunningLocked() bool {
	return procAlive(m.child, m.childDone)
}

func (m *Manager) IsRunning() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.isRunningLocked()
}

func (m *Manager) isMaintenanceRunningLocked() bool {
	return procAlive(m.maintenance, m.maintenanceDone)
}

func (m *Manager) GetRuntimeState() RuntimeState {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := m.runtimeState
	out.Running = m.isRunningLocked() && m.runtimeState.Started
	return out
}

func (m *Manager) GetLastCrash() map[string]any {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.lastCrash == nil {
		return nil
	}
	out := make(map[string]any, len(m.lastCrash))
	for k, v := range m.lastCrash {
		out[k] = v
	}
	return out
}

func (m *Manager) GetJoinedLogs() map[string]string {
	m.mu.Lock()
	defer m.mu.Unlock()
	return map[string]string{
		"stdout": strings.Join(m.logBuffers["stdout"], ""),
		"stderr": strings.Join(m.logBuffers["stderr"], ""),
	}
}

func (m *Manager) GetStartupDiagnostics() map[string]any {
	m.mu.Lock()
	state := m.runtimeState
	state.Running = m.isRunningLocked() && m.runtimeState.Started
	var crash any
	if m.lastCrash != nil {
		cp := make(map[string]any, len(m.lastCrash))
		for k, v := range m.lastCrash {
			cp[k] = v
		}
		crash = cp
	}
	m.mu.Unlock()
	return map[string]any{
		"runtime": state,
		"crash":   crash,
		"paths":   crashreport.DiagnosticPaths(m.deps.StorageDir(), m.deps.ReticulumConfigDir()),
	}
}

func pushLogLine(buf []string, line string) []string {
	buf = append(buf, line)
	if len(buf) > LogLineCap {
		buf = buf[1:]
	}
	return buf
}

func (m *Manager) recordCrash(code *int, signal string) {
	logs := m.GetJoinedLogs()
	m.mu.Lock()
	crash := &crashreport.Crash{
		Code: code, Signal: signal, Stdout: logs["stdout"], Stderr: logs["stderr"],
		At: time.Now().UnixMilli(), Pid: m.runtimeState.Pid, Platform: runtime.GOOS,
	}
	m.lastCrash = crashToMap(crash)
	m.mu.Unlock()
	crashreport.PersistCrashReport(m.deps.StorageDir(), crash)
}

func (m *Manager) notifyStartupFailure(code *int, signal string) {
	paths := crashreport.DiagnosticPaths(m.deps.StorageDir(), m.deps.ReticulumConfigDir())
	m.mu.Lock()
	var stdout, stderr string
	var at int64 = time.Now().UnixMilli()
	if m.lastCrash != nil {
		if s, ok := m.lastCrash["stdout"].(string); ok {
			stdout = s
		}
		if s, ok := m.lastCrash["stderr"].(string); ok {
			stderr = s
		}
		if f, ok := m.lastCrash["at"].(float64); ok {
			at = int64(f)
		}
	}
	m.mu.Unlock()
	payload := map[string]any{
		"code": code, "signal": signal, "at": at,
		"stdout": stdout, "stderr": stderr, "paths": paths,
	}
	m.deps.NotifyRenderer("backend-startup-failed", payload)
	m.deps.NotifyRenderer("backend-process-exited", map[string]any{
		"code": code, "signal": signal, "at": at,
	})
}

func (m *Manager) buildSpawnEnv() []string {
	env := os.Environ()
	logsDir := crashreport.GetLogsDir(m.deps.StorageDir())
	extra := map[string]string{
		"MESHCHAT_LOG_DIR":              logsDir,
		"MESHCHAT_STORAGE_DIR":          m.deps.StorageDir(),
		"MESHCHAT_RETICULUM_CONFIG_DIR": m.deps.ReticulumConfigDir(),
	}
	for k, v := range system.BackendMemoryEnv(env) {
		extra[k] = v
	}
	// Override existing keys.
	out := make([]string, 0, len(env)+len(extra))
	seen := map[string]bool{}
	for _, kv := range env {
		key := kv
		if i := strings.Index(kv, "="); i >= 0 {
			key = kv[:i]
		}
		if _, ok := extra[key]; ok {
			seen[key] = true
			continue
		}
		out = append(out, kv)
	}
	for k, v := range extra {
		if !seen[k] {
			out = append(out, k+"="+v)
		}
	}
	return out
}

// appContainerEnabled is a var so tests can stub the Windows-only gate.
var appContainerEnabled = func() bool {
	if runtime.GOOS != "windows" {
		return false
	}
	raw := strings.TrimSpace(strings.ToLower(os.Getenv("MESHCHAT_APPCONTAINER")))
	if raw == "" {
		return false
	}
	switch raw {
	case "true", "1", "yes", "on", "auto":
		return true
	}
	return false
}

func (m *Manager) buildBackendArgs(extraArgs []string) []string {
	m.mu.Lock()
	userArgs := append([]string(nil), m.userArgs...)
	m.mu.Unlock()

	args := []string{"--headless", "--port", "9337"}
	if !paths.HasArgvFlag(userArgs, "--reticulum-config-dir") {
		args = append(args, "--reticulum-config-dir", m.deps.ReticulumConfigDir())
	}
	if !paths.HasArgvFlag(userArgs, "--storage-dir") {
		args = append(args, "--storage-dir", m.deps.StorageDir())
	}
	args = append(args, userArgs...)
	args = append(args, extraArgs...)
	return args
}

func (m *Manager) buildSpawnArgs(extraArgs []string) []string {
	backendArgs := m.buildBackendArgs(extraArgs)
	if !appContainerEnabled() {
		return backendArgs
	}
	return append([]string{"--meshchatx-run-module", "meshchatx.src.backend.appcontainer_launcher"}, backendArgs...)
}

// SpawnBackend starts the backend executable. Returns {ok,pid} or error.
// spawnMu makes the is-running check, orphan sweep and registration atomic
// so two concurrent callers cannot both spawn a backend.
func (m *Manager) SpawnBackend(exePath string, integrityRef *integrity.Result) (map[string]any, error) {
	if exePath == "" {
		return nil, fmt.Errorf("Backend executable path is not set.")
	}
	m.spawnMu.Lock()
	defer m.spawnMu.Unlock()
	m.mu.Lock()
	if m.isRunningLocked() {
		m.mu.Unlock()
		return map[string]any{"ok": true, "alreadyRunning": true}, nil
	}
	if m.isMaintenanceRunningLocked() {
		m.mu.Unlock()
		return nil, fmt.Errorf("A backend maintenance task is still running.")
	}
	var maintenancePid *int
	if m.isMaintenanceRunningLocked() && m.maintenance.Process != nil {
		pid := m.maintenance.Process.Pid
		maintenancePid = &pid
	}
	m.mu.Unlock()

	removed, err := KillOrphanBackendProcesses(maintenancePid)
	if err != nil {
		m.deps.Log(fmt.Sprintf("Orphan sweep failed: %v", err))
	}
	if removed > 0 {
		m.deps.Log(fmt.Sprintf("Removed %d orphan backend process(es) before startup.", removed))
	}

	m.mu.Lock()
	m.resolvedExe = exePath
	exeDir := filepath.Dir(exePath)
	m.mu.Unlock()

	if integrityRef != nil {
		res := integrity.VerifyBackendIntegrity(exeDir)
		*integrityRef = res
		m.mu.Lock()
		m.integrity = &res
		m.mu.Unlock()
		if res.OK && len(res.Issues) == 1 && res.Issues[0] == "Manifest missing" {
			m.deps.Log("Backend integrity manifest missing, skipping check.")
		}
		if !res.OK {
			m.deps.Log(fmt.Sprintf("INTEGRITY WARNING: Backend tampering detected! Issues: %s", strings.Join(res.Issues, ", ")))
		}
	}

	if appContainerEnabled() {
		m.deps.Log("Starting Windows backend via AppContainer launcher.")
	}

	args := m.buildSpawnArgs(nil)
	cmd := exec.Command(exePath, args...)
	cmd.Env = m.buildSpawnEnv()
	applySysProcAttr(cmd)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, err
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return nil, err
	}
	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("Failed to start backend process: %w", err)
	}
	pid := cmd.Process.Pid

	m.mu.Lock()
	m.child = cmd
	m.childDone = make(chan struct{})
	m.childExitCode = nil
	m.childExitSignal = ""
	m.logBuffers = map[string][]string{"stdout": {}, "stderr": {}}
	m.runtimeState = RuntimeState{
		Started: true, Running: true, Pid: &pid,
		LastExitSignal: "", LastError: "",
		LastEventAt: int64Ptr(time.Now().UnixMilli()),
	}
	m.mu.Unlock()

	m.wireChild(cmd, stdout, stderr, false)
	return map[string]any{"ok": true, "pid": pid}, nil
}

func int64Ptr(v int64) *int64 { return &v }

func (m *Manager) wireChild(cmd *exec.Cmd, stdout, stderr interface{ Read([]byte) (int, error) }, isMaintenance bool) {
	// Stdout/stderr pumping.
	pump := func(streamName string, r interface{ Read([]byte) (int, error) }) {
		scanner := bufio.NewScanner(r)
		scanner.Buffer(make([]byte, 64*1024), 1024*1024)
		for scanner.Scan() {
			text := scanner.Text() + "\n"
			if m.deps.SpoolStdoutToLog {
				m.deps.Log(text)
			}
			m.mu.Lock()
			m.logBuffers[streamName] = pushLogLine(m.logBuffers[streamName], text)
			m.mu.Unlock()
		}
	}
	go pump("stdout", stdout)
	go pump("stderr", stderr)

	done := make(chan struct{})
	go func() {
		err := cmd.Wait()
		code := -1
		signal := ""
		if err == nil {
			code = 0
		} else if ee, ok := err.(*exec.ExitError); ok {
			if ws, ok := ee.Sys().(syscall.WaitStatus); ok {
				if ws.Signaled() {
					signal = ws.Signal().String()
					code = -1
				} else {
					code = ws.ExitStatus()
				}
			} else {
				code = ee.ExitCode()
			}
		}
		var codePtr *int
		if code >= 0 {
			codePtr = &code
		}
		m.mu.Lock()
		if isMaintenance {
			m.maintenanceExitCode = codePtr
			if m.maintenance == cmd {
				m.maintenance = nil
			}
		} else {
			m.childExitCode = codePtr
			m.childExitSignal = signal
			if m.child == cmd {
				m.child = nil
			}
		}
		m.mu.Unlock()
		close(done)

		if isMaintenance {
			return
		}
		m.handleChildExit(codePtr, signal)
	}()

	if isMaintenance {
		m.mu.Lock()
		m.maintenanceDone = done
		m.mu.Unlock()
	} else {
		m.mu.Lock()
		m.childDone = done
		m.mu.Unlock()
	}
}

func (m *Manager) handleChildExit(code *int, signal string) {
	m.mu.Lock()
	m.runtimeState.Running = false
	m.runtimeState.LastExitCode = code
	m.runtimeState.LastExitSignal = signal
	m.runtimeState.LastEventAt = int64Ptr(time.Now().UnixMilli())
	m.mu.Unlock()

	if m.deps.IsQuiting() {
		return
	}
	if code == nil && signal == "" {
		return
	}

	m.recordCrash(code, signal)

	page := m.deps.MainWindowPageKind()
	switch page {
	case "loading":
		m.notifyStartupFailure(code, signal)
		return
	case "app", "crash":
		m.deps.NotifyRenderer("backend-process-exited", map[string]any{
			"code": code, "signal": signal, "at": crashAt(m.lastCrashOrNil()),
		})
		return
	}

	m.deps.NotifyRenderer("backend-process-exited", map[string]any{
		"code": code, "signal": signal, "at": crashAt(m.lastCrashOrNil()),
	})
	if crash := m.lastCrashOrNil(); crash != nil {
		m.deps.ShowCrashPage(crash)
	}
}

func (m *Manager) lastCrashOrNil() map[string]any {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.lastCrash
}

func crashAt(crash map[string]any) any {
	if crash == nil {
		return time.Now().UnixMilli()
	}
	return crash["at"]
}

func (m *Manager) MarkBackendHealthy() {
	m.mu.Lock()
	m.runtimeState.LastExitCode = nil
	m.runtimeState.LastError = ""
	m.lastCrash = nil
	m.mu.Unlock()
	crashreport.ClearCrashReport(m.deps.StorageDir())
}

// RestartBackend respawns the resolved executable.
func (m *Manager) RestartBackend(integrityRef *integrity.Result) map[string]any {
	m.mu.Lock()
	exe := m.resolvedExe
	m.mu.Unlock()
	if exe == "" {
		return map[string]any{"ok": false, "error": "Backend executable is not configured."}
	}
	if m.IsRunning() {
		return map[string]any{"ok": false, "error": "Backend is already running."}
	}
	res, err := m.SpawnBackend(exe, integrityRef)
	if err != nil {
		return map[string]any{"ok": false, "error": err.Error()}
	}
	return map[string]any{"ok": true, "pid": res["pid"]}
}

// ChildProcess returns the managed backend or maintenance child for quit().
func (m *Manager) ChildProcess() *exec.Cmd {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.child != nil {
		return m.child
	}
	return m.maintenance
}

func signalProcess(cmd *exec.Cmd, done chan struct{}, sig syscall.Signal) {
	if !procAlive(cmd, done) {
		return
	}
	if runtime.GOOS == "windows" {
		_ = exec.Command("taskkill", "/F", "/T", "/PID", strconv.Itoa(cmd.Process.Pid)).Run()
		return
	}
	_ = cmd.Process.Signal(sig)
}

// KillChild signals both managed children.
func (m *Manager) KillChild(sig syscall.Signal) {
	m.mu.Lock()
	child, childDone := m.child, m.childDone
	maint, maintDone := m.maintenance, m.maintenanceDone
	m.mu.Unlock()
	signalProcess(child, childDone, sig)
	signalProcess(maint, maintDone, sig)
}

func waitExit(done chan struct{}, timeout time.Duration) {
	if done == nil {
		return
	}
	select {
	case <-done:
	case <-time.After(timeout):
	}
}

// RunMaintenanceTask runs the backend with extra args (no --headless spawn of
// the UI): waits for a running backend to exit first, then captures output.
func (m *Manager) RunMaintenanceTask(extraArgs []string) map[string]any {
	m.mu.Lock()
	exe := m.resolvedExe
	m.mu.Unlock()
	if exe == "" {
		return map[string]any{"ok": false, "error": "Backend executable is not configured."}
	}
	m.mu.Lock()
	if m.isMaintenanceRunningLocked() {
		m.mu.Unlock()
		return map[string]any{"ok": false, "error": "A backend maintenance task is already running."}
	}
	var running *exec.Cmd
	var runningDone chan struct{}
	if m.isRunningLocked() {
		running = m.child
		runningDone = m.childDone
	}
	m.mu.Unlock()

	if running != nil {
		m.KillChild(syscall.SIGTERM)
		waitExit(runningDone, 5*time.Second)
		if !procExited(runningDone) {
			m.KillChild(syscall.SIGKILL)
			waitExit(runningDone, 2*time.Second)
		}
	}

	args := m.buildSpawnArgs(extraArgs)
	cmd := exec.Command(exe, args...)
	cmd.Env = m.buildSpawnEnv()
	applySysProcAttr(cmd)

	var stdoutBuf, stderrBuf bytes.Buffer
	cmd.Stdout = &stdoutBuf
	cmd.Stderr = &stderrBuf

	startErr := cmd.Start()
	if startErr != nil {
		return map[string]any{
			"ok": false, "error": fmt.Sprintf("Failed to start backend maintenance task: %v", startErr),
			"stdout": "", "stderr": "",
		}
	}

	done := make(chan struct{})
	// resCh carries the wait outcome so callers never touch cmd.ProcessState
	// or the stdout/stderr buffers while cmd.Wait is still running — reading
	// them concurrently races with Wait's copy goroutines.
	type waitResult struct {
		code    int
		stdout  string
		stderr  string
	}
	resCh := make(chan waitResult, 1)
	m.mu.Lock()
	m.maintenance = cmd
	m.maintenanceDone = done
	m.mu.Unlock()
	go func() {
		defer close(done)
		err := cmd.Wait()
		code := 0
		if ee, ok := err.(*exec.ExitError); ok {
			code = ee.ExitCode()
		} else if err != nil {
			code = -1
		}
		resCh <- waitResult{code: code, stdout: stdoutBuf.String(), stderr: stderrBuf.String()}
	}()

	// A hung maintenance child must not wedge the manager forever: bound the
	// wait, then escalate SIGTERM -> SIGKILL like shutdownBackend does.
	timedOut := false
	var res waitResult
	select {
	case res = <-resCh:
	case <-time.After(maintenanceTaskTimeout):
		timedOut = true
		m.KillChild(syscall.SIGTERM)
		waitExit(done, 5*time.Second)
		if !procExited(done) {
			m.KillChild(syscall.SIGKILL)
			waitExit(done, 2*time.Second)
		}
		select {
		case res = <-resCh:
		default:
			// SIGKILL could not reap it (e.g. uninterruptible I/O). Report the
			// timeout rather than touch state cmd.Wait still owns.
			m.mu.Lock()
			if m.maintenance == cmd {
				m.maintenance = nil
			}
			m.mu.Unlock()
			return map[string]any{
				"ok":    false,
				"error": "Maintenance task timed out and could not be terminated.",
			}
		}
	}
	m.mu.Lock()
	if m.maintenance == cmd {
		m.maintenance = nil
	}
	m.mu.Unlock()

	stdout := res.stdout
	stderr := res.stderr
	if timedOut {
		return map[string]any{
			"ok": false, "error": "Maintenance task timed out.",
			"stdout": stdout, "stderr": stderr,
		}
	}
	if res.code == 0 {
		return map[string]any{"ok": true, "exitCode": res.code, "stdout": stdout, "stderr": stderr}
	}
	return map[string]any{
		"ok": false, "exitCode": res.code,
		"error":  fmt.Sprintf("Maintenance task exited with code %d", res.code),
		"stdout": stdout, "stderr": stderr,
	}
}

// applySysProcAttr is defined per-platform (procattr_<os>.go).

// ---- orphan cleanup (backendProcessOrphans.js) ----------------------------

func isHeadlessBackendArgs(args string) bool {
	if args == "" || !strings.Contains(args, BackendImageName) {
		return false
	}
	return strings.Contains(args, " --headless ") || strings.HasSuffix(args, " --headless") || strings.Contains(args, "\t--headless")
}

func listUnixBackendPids(excludePids map[int]bool) []int {
	if runtime.GOOS == "windows" {
		return nil
	}
	out, err := exec.Command("ps", "-eo", "pid=,args=").Output()
	if err != nil {
		return nil
	}
	var pids []int
	self := os.Getpid()
	scanner := bufio.NewScanner(bytes.NewReader(out))
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		idx := strings.IndexFunc(line, func(r rune) bool { return r == ' ' || r == '\t' })
		if idx <= 0 {
			continue
		}
		pid, err := strconv.Atoi(line[:idx])
		args := strings.TrimSpace(line[idx:])
		if err != nil || pid <= 0 || args == "" {
			continue
		}
		if excludePids[pid] || pid == self {
			continue
		}
		if isHeadlessBackendArgs(args) {
			pids = append(pids, pid)
		}
	}
	return pids
}

// KillOrphanBackendProcesses terminates leftover headless backend processes,
// excluding ownPid (e.g. a maintenance child). Returns the killed count.
func KillOrphanBackendProcesses(ownPid *int) (int, error) {
	exclude := map[int]bool{}
	if ownPid != nil {
		exclude[*ownPid] = true
	}
	return killOrphanBackendPids(exclude), nil
}
