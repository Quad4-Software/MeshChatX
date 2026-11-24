//go:build !windows

package backendproc

import (
	"errors"
	"os/exec"
	"syscall"
	"time"
)

// deliverSignal signals the child's whole process group: children spawn with
// Setsid so the backend pid is also its process-group id. Falls back to the
// single pid when the group is already gone or not signalable.
func deliverSignal(cmd *exec.Cmd, sig syscall.Signal) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	pid := cmd.Process.Pid
	if err := syscall.Kill(-pid, sig); err == nil {
		return
	} else if !errors.Is(err, syscall.ESRCH) && !errors.Is(err, syscall.EPERM) {
		return
	}
	_ = cmd.Process.Signal(sig)
}

// KillUnixPids SIGTERMs pids, waits up to 1.5s, then SIGKILLs survivors.
func KillUnixPids(pids []int) int {
	if len(pids) == 0 {
		return 0
	}
	killed := make(map[int]bool, len(pids))
	for _, pid := range pids {
		if err := syscall.Kill(pid, syscall.SIGTERM); err == nil {
			killed[pid] = true
		}
	}
	deadline := time.Now().Add(1500 * time.Millisecond)
	for time.Now().Before(deadline) {
		remaining := 0
		for _, pid := range pids {
			if syscall.Kill(pid, 0) == nil {
				remaining++
			}
		}
		if remaining == 0 {
			return len(killed)
		}
		time.Sleep(50 * time.Millisecond)
	}
	for _, pid := range pids {
		if err := syscall.Kill(pid, syscall.SIGKILL); err == nil {
			killed[pid] = true
		}
	}
	return len(killed)
}
