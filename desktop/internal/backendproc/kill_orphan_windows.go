//go:build windows

package backendproc

import (
	"os/exec"
	"strconv"
)

func killOrphanBackendPids(exclude map[int]bool) int {
	pids := listWindowsBackendPids(exclude)
	for _, pid := range pids {
		_ = exec.Command("taskkill", "/F", "/T", "/PID", strconv.Itoa(pid)).Run()
	}
	return len(pids)
}
