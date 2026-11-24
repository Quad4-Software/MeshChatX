//go:build !windows

package backendproc

import (
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"testing"
	"time"
)

func pidAlive(pid int) bool {
	return syscall.Kill(pid, 0) == nil
}

func waitDead(t *testing.T, pid int) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if !pidAlive(pid) {
			return
		}
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatalf("pid %d still alive", pid)
}

func TestDeliverSignalKillsProcessGroup(t *testing.T) {
	dir := t.TempDir()
	pidFile := filepath.Join(dir, "gpid")
	cmd := exec.Command("sh", "-c", "sleep 60 & echo $! > "+pidFile+"; wait")
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err := cmd.Start(); err != nil {
		t.Skipf("sh unavailable: %v", err)
	}
	defer func() {
		_ = syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
	}()
	var gpid int
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if data, err := os.ReadFile(pidFile); err == nil {
			if n, err := strconv.Atoi(strings.TrimSpace(string(data))); err == nil {
				gpid = n
				break
			}
		}
		time.Sleep(20 * time.Millisecond)
	}
	if gpid == 0 {
		t.Fatal("grandchild pid file never appeared")
	}
	deliverSignal(cmd, syscall.SIGKILL)
	_ = cmd.Wait()
	waitDead(t, cmd.Process.Pid)
	waitDead(t, gpid)
}

func TestDeliverSignalFallbackSinglePid(t *testing.T) {
	cmd := exec.Command("sleep", "60")
	if err := cmd.Start(); err != nil {
		t.Skipf("sleep unavailable: %v", err)
	}
	defer func() { _ = cmd.Process.Kill(); _ = cmd.Wait() }()
	time.Sleep(50 * time.Millisecond)
	deliverSignal(cmd, syscall.SIGKILL)
	_ = cmd.Wait()
	waitDead(t, cmd.Process.Pid)
}
