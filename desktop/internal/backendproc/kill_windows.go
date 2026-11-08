//go:build windows

package backendproc

import (
	"os"
	"os/exec"
	"strconv"
	"strings"
)

func listWindowsBackendPids(excludePids map[int]bool) []int {
	// PowerShell CIM query for processes whose command line looks like the
	// headless backend. Excludes the current PID.
	ps := `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ReticulumMeshChatX*' -and $_.CommandLine -like '*--headless*' } | ForEach-Object { $_.ProcessId }`
	out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", ps).Output()
	if err != nil {
		return nil
	}
	var pids []int
	self := os.Getpid()
	for _, tok := range strings.Fields(string(out)) {
		pid, err := strconv.Atoi(tok)
		if err != nil || pid <= 0 || pid == self || excludePids[pid] {
			continue
		}
		pids = append(pids, pid)
	}
	return pids
}

// KillUnixPids is never reached on Windows (KillOrphanBackendProcesses uses
// taskkill there); it exists so the shared call site compiles.
func KillUnixPids([]int) {}
