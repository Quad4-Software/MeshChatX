//go:build windows

package backendproc

import (
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

// deliverSignal kills the child and its whole tree; taskkill /T already
// covers descendants, matching the unix process-group kill.
func deliverSignal(cmd *exec.Cmd, sig syscall.Signal) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	_ = exec.Command("taskkill", "/F", "/T", "/PID", strconv.Itoa(cmd.Process.Pid)).Run()
}

func listWindowsBackendPids(excludePids map[int]bool, exePath string) []int {
	if exePath == "" {
		return nil
	}
	wantExe := strings.ToLower(filepath.Clean(exePath))
	// PowerShell CIM query for processes whose command line looks like the
	// headless backend. Excludes the current PID.
	ps := `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ReticulumMeshChatX*' -and $_.CommandLine -like '*--headless*' } | ForEach-Object { "$($_.ProcessId)|$($_.ExecutablePath)" }`
	out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", ps).Output()
	if err != nil {
		return nil
	}
	var pids []int
	self := os.Getpid()
	for _, line := range strings.Split(string(out), "\n") {
		fields := strings.SplitN(strings.TrimSpace(line), "|", 2)
		pid, err := strconv.Atoi(fields[0])
		if err != nil || pid <= 0 || pid == self || excludePids[pid] {
			continue
		}
		if len(fields) < 2 || strings.ToLower(filepath.Clean(fields[1])) != wantExe {
			continue
		}
		pids = append(pids, pid)
	}
	return pids
}

// KillUnixPids is never reached on Windows (KillOrphanBackendProcesses uses
// taskkill there); it exists so the shared call site compiles.
func KillUnixPids([]int) int { return 0 }
