package backendproc

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"
)

type recordedEvent struct {
	channel string
	payload any
}

type testDeps struct {
	mu       sync.Mutex
	events   []recordedEvent
	logs     []string
	storage  string
	rns      string
	pageKind string
	quiting  bool
}

func (d *testDeps) Log(msg string) {
	d.mu.Lock()
	d.logs = append(d.logs, msg)
	d.mu.Unlock()
}

func (d *testDeps) eventChannels() []string {
	d.mu.Lock()
	defer d.mu.Unlock()
	out := make([]string, 0, len(d.events))
	for _, e := range d.events {
		out = append(out, e.channel)
	}
	return out
}

func (d *testDeps) hasEvent(channel string) bool {
	for _, ch := range d.eventChannels() {
		if ch == channel {
			return true
		}
	}
	return false
}

func newTestManager(t *testing.T) (*Manager, *testDeps) {
	t.Helper()
	dir := t.TempDir()
	d := &testDeps{storage: dir, rns: filepath.Join(dir, "rns"), pageKind: "app"}
	deps := Deps{
		Log:                d.Log,
		StorageDir:         func() string { return d.storage },
		ReticulumConfigDir: func() string { return d.rns },
		MainWindowPageKind: func() string { return d.pageKind },
		IsQuiting:          func() bool { return d.quiting },
		NotifyRenderer: func(channel string, payload any) {
			d.mu.Lock()
			d.events = append(d.events, recordedEvent{channel, payload})
			d.mu.Unlock()
		},
		ShowCrashPage: func(crash map[string]any) {
			d.mu.Lock()
			d.events = append(d.events, recordedEvent{"show-crash-page", crash})
			d.mu.Unlock()
		},
		SpoolStdoutToLog: false,
	}
	return NewManager(deps), d
}

func writeStubBackend(t *testing.T, dir, name, body string) string {
	t.Helper()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	p := filepath.Join(dir, name)
	if err := os.WriteFile(p, []byte(body), 0o755); err != nil {
		t.Fatal(err)
	}
	return p
}

func waitFor(t *testing.T, what string, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(8 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatalf("timeout waiting for %s", what)
}

func TestBuildBackendArgs(t *testing.T) {
	m, _ := newTestManager(t)
	m.SetUserProvidedArguments([]string{"--verbose"})
	args := m.buildBackendArgs([]string{"--restore-db", "/tmp/x.zip"})
	if args[0] != "--headless" || args[1] != "--port" || args[2] != "9337" {
		t.Fatalf("base args: %v", args[:3])
	}
	joined := strings.Join(args, " ")
	for _, want := range []string{"--reticulum-config-dir", "--storage-dir", "--verbose", "--restore-db"} {
		if !strings.Contains(joined, want) {
			t.Errorf("missing %s in %v", want, args)
		}
	}
	// user-provided dirs are not duplicated
	m2, _ := newTestManager(t)
	m2.SetUserProvidedArguments([]string{"--storage-dir", "/custom", "--reticulum-config-dir", "/rns"})
	args2 := m2.buildBackendArgs(nil)
	count := 0
	for _, a := range args2 {
		if a == "--storage-dir" {
			count++
		}
	}
	if count != 1 {
		t.Fatalf("--storage-dir should appear once, got %v", args2)
	}
}

func TestBuildSpawnArgsAppContainer(t *testing.T) {
	m, _ := newTestManager(t)
	orig := appContainerEnabled
	defer func() { appContainerEnabled = orig }()

	appContainerEnabled = func() bool { return false }
	if got := m.buildSpawnArgs(nil); got[0] == "--meshchatx-run-module" {
		t.Fatal("unexpected appcontainer prefix")
	}
	appContainerEnabled = func() bool { return true }
	got := m.buildSpawnArgs(nil)
	if len(got) < 3 || got[0] != "--meshchatx-run-module" ||
		got[1] != "meshchatx.src.backend.appcontainer_launcher" {
		t.Fatalf("appcontainer prefix missing: %v", got)
	}
}

func TestIsHeadlessBackendArgs(t *testing.T) {
	cases := []struct {
		args string
		want bool
	}{
		{"/x/backend/ReticulumMeshChatX --headless --port 9337", true},
		{"ReticulumMeshChatX --headless", true},
		{"ReticulumMeshChatX\t--headless", true},
		{"/x/ReticulumMeshChatX --port 9337", false},
		{"/x/other --headless", false},
		{"", false},
		{"ReticulumMeshChatX --headlessish", false},
	}
	for _, tc := range cases {
		if got := isHeadlessBackendArgs(tc.args); got != tc.want {
			t.Errorf("%q: got %v want %v", tc.args, got, tc.want)
		}
	}
}

func TestPushLogLineCap(t *testing.T) {
	var buf []string
	for i := 0; i < LogLineCap+50; i++ {
		buf = pushLogLine(buf, "x")
	}
	if len(buf) != LogLineCap {
		t.Fatalf("cap: %d", len(buf))
	}
}

func TestSpawnAndExit(t *testing.T) {
	m, d := newTestManager(t)
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX", "#!/bin/sh\nsleep 30\n")
	res, err := m.SpawnBackend(exe, nil)
	if err != nil {
		t.Fatal(err)
	}
	if res["ok"] != true {
		t.Fatalf("spawn: %v", res)
	}
	pid, _ := res["pid"].(int)
	if pid <= 0 {
		t.Fatalf("pid: %v", res)
	}
	state := m.GetRuntimeState()
	if !state.Started || !state.Running || state.Pid == nil || *state.Pid != pid {
		t.Fatalf("runtime state: %+v", state)
	}

	// already-running guard
	res2, err2 := m.SpawnBackend(exe, nil)
	if err2 != nil || res2["alreadyRunning"] != true {
		t.Fatalf("second spawn: %v %v", res2, err2)
	}

	// kill child -> exit handling -> backend-process-exited event
	m.KillChild(syscall.SIGTERM)
	waitFor(t, "child exit", func() bool { return !m.IsRunning() })
	waitFor(t, "backend-process-exited event", func() bool {
		return d.hasEvent("backend-process-exited")
	})
}

func TestSpawnFailure(t *testing.T) {
	m, _ := newTestManager(t)
	if _, err := m.SpawnBackend("", nil); err == nil {
		t.Fatal("empty exe should fail")
	}
	if _, err := m.SpawnBackend(filepath.Join(t.TempDir(), "nope"), nil); err == nil {
		t.Fatal("missing exe should fail")
	}
}

func TestCrashReportPersistedOnExit(t *testing.T) {
	m, d := newTestManager(t)
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX",
		"#!/bin/sh\necho out-line\necho err-line >&2\nexit 3\n")
	if _, err := m.SpawnBackend(exe, nil); err != nil {
		t.Fatal(err)
	}
	waitFor(t, "crash recorded", func() bool { return m.GetLastCrash() != nil })

	crash := m.GetLastCrash()
	if crash["signal"] != "" {
		t.Fatalf("expected exit code not signal: %v", crash)
	}
	if _, err := os.Stat(filepath.Join(d.storage, "logs", "last-backend-crash.json")); err != nil {
		t.Fatalf("crash report not persisted: %v", err)
	}
	logs := m.GetJoinedLogs()
	if !strings.Contains(logs["stdout"], "out-line") || !strings.Contains(logs["stderr"], "err-line") {
		t.Fatalf("logs: %+v", logs)
	}
	m.MarkBackendHealthy()
	if m.GetLastCrash() != nil {
		t.Fatal("crash not cleared")
	}
	if _, err := os.Stat(filepath.Join(d.storage, "logs", "last-backend-crash.json")); !os.IsNotExist(err) {
		t.Fatal("crash report file not removed")
	}
}

func TestSpawnBackendConcurrentSingleProcess(t *testing.T) {
	m, _ := newTestManager(t)
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX", "#!/bin/sh\nsleep 30\n")
	var wg sync.WaitGroup
	results := make([]map[string]any, 2)
	errs := make([]error, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			results[i], errs[i] = m.SpawnBackend(exe, nil)
		}(i)
	}
	wg.Wait()
	spawned, already := 0, 0
	for i := range results {
		if errs[i] != nil {
			t.Fatalf("spawn %d: %v", i, errs[i])
		}
		if results[i]["alreadyRunning"] == true {
			already++
		} else if results[i]["ok"] == true && results[i]["pid"] != nil {
			spawned++
		}
	}
	if spawned != 1 || already != 1 {
		t.Fatalf("expected one spawn + one alreadyRunning, got %+v", results)
	}
	m.KillChild(syscall.SIGKILL)
	waitFor(t, "child exit", func() bool { return !m.IsRunning() })
}

func TestMaintenanceTaskTimeout(t *testing.T) {
	orig := maintenanceTaskTimeout
	maintenanceTaskTimeout = 300 * time.Millisecond
	defer func() { maintenanceTaskTimeout = orig }()

	m, _ := newTestManager(t)
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX", "#!/bin/sh\nsleep 60\n")
	m.ResolveExecutablePath(func() string { return exe })
	start := time.Now()
	res := m.RunMaintenanceTask(nil)
	if res["ok"] != false {
		t.Fatalf("hung task should fail: %v", res)
	}
	if !strings.Contains(fmt.Sprint(res["error"]), "timed out") {
		t.Fatalf("expected timeout error: %v", res["error"])
	}
	if elapsed := time.Since(start); elapsed > 20*time.Second {
		t.Fatalf("kill escalation took too long: %v", elapsed)
	}
	// Manager must be usable again after the kill.
	m.mu.Lock()
	stillRunning := m.isMaintenanceRunningLocked()
	m.mu.Unlock()
	if stillRunning {
		t.Fatal("maintenance still marked running after timeout")
	}
}

func TestMaintenanceTask(t *testing.T) {
	m, _ := newTestManager(t)
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX",
		"#!/bin/sh\necho maint-out\nexit 0\n")
	m.ResolveExecutablePath(func() string { return exe })
	res := m.RunMaintenanceTask([]string{"--restore-db", "/tmp/b.zip"})
	if res["ok"] != true {
		t.Fatalf("maintenance: %v", res)
	}
	if !strings.Contains(res["stdout"].(string), "maint-out") {
		t.Fatalf("stdout: %v", res["stdout"])
	}
}

func TestMaintenanceTaskFailure(t *testing.T) {
	m, _ := newTestManager(t)
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX", "#!/bin/sh\nexit 7\n")
	m.ResolveExecutablePath(func() string { return exe })
	res := m.RunMaintenanceTask(nil)
	if res["ok"] != false || res["exitCode"] != 7 {
		t.Fatalf("maintenance failure: %v", res)
	}
}

func TestRestartBackend(t *testing.T) {
	m, _ := newTestManager(t)
	if res := m.RestartBackend(nil); res["ok"] != false {
		t.Fatalf("restart without exe: %v", res)
	}
	exe := writeStubBackend(t, t.TempDir(), "ReticulumMeshChatX", "#!/bin/sh\nsleep 30\n")
	m.ResolveExecutablePath(func() string { return exe })
	res := m.RestartBackend(nil)
	if res["ok"] != true {
		t.Fatalf("restart: %v", res)
	}
	if !m.IsRunning() {
		t.Fatal("backend not running after restart")
	}
	if res := m.RestartBackend(nil); res["ok"] != false {
		t.Fatalf("restart while running: %v", res)
	}
	m.KillChild(syscall.SIGKILL)
	waitFor(t, "child exit after kill", func() bool { return !m.IsRunning() })
}

func TestKillOrphanBackendProcesses(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("unix-only test")
	}
	// Spawn a process whose cmdline matches the headless-backend pattern.
	cmd := exec.Command("bash", "-c", "sleep 60 & wait", "ReticulumMeshChatX", "--headless")
	if err := cmd.Start(); err != nil {
		t.Skipf("cannot spawn marker process: %v", err)
	}
	markerPid := cmd.Process.Pid
	defer func() {
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
	}()
	time.Sleep(100 * time.Millisecond)

	// self pid must be excluded
	selfPid := os.Getpid()
	pids := listUnixBackendPids(map[int]bool{selfPid: true})
	found := false
	for _, p := range pids {
		if p == markerPid {
			found = true
		}
	}
	if !found {
		t.Fatalf("marker pid %d not found in %v", markerPid, pids)
	}

	removed, err := KillOrphanBackendProcesses(nil)
	if err != nil {
		t.Fatal(err)
	}
	if removed < 1 {
		t.Fatal("no orphans removed")
	}
	// The killed bash becomes a zombie until reaped; Wait() collects it.
	waitDone := make(chan struct{})
	go func() { _ = cmd.Wait(); close(waitDone) }()
	select {
	case <-waitDone:
	case <-time.After(3 * time.Second):
		t.Fatal("marker process did not exit after orphan sweep")
	}
	if cmd.ProcessState == nil || cmd.ProcessState.Success() {
		t.Fatalf("marker should have been killed: %v", cmd.ProcessState)
	}
}
