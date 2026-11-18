//go:build !windows

package backendproc

import (
	"syscall"
	"time"
)

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
