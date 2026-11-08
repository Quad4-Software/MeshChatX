//go:build !windows

package backendproc

import (
	"syscall"
	"time"
)

// KillUnixPids SIGTERMs pids, waits up to 1.5s, then SIGKILLs survivors.
func KillUnixPids(pids []int) {
	if len(pids) == 0 {
		return
	}
	for _, pid := range pids {
		_ = syscall.Kill(pid, syscall.SIGTERM)
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
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	for _, pid := range pids {
		_ = syscall.Kill(pid, syscall.SIGKILL)
	}
}
