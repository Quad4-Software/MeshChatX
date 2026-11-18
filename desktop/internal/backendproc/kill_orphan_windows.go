//go:build windows

package backendproc

import (
	"os/exec"
	"strconv"
)

func killOrphanBackendPids(exclude map[int]bool, exePath string) int {
	pids := listWindowsBackendPids(exclude, exePath)
	removed := 0
	for _, pid := range pids {
		if err := exec.Command("taskkill", "/F", "/T", "/PID", strconv.Itoa(pid)).Run(); err == nil {
			removed++
		}
	}
	return removed
}
