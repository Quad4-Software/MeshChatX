//go:build !windows

package backendproc

import (
	"os/exec"
	"syscall"
)

// applySysProcAttr detaches the backend into its own session on Unix so it
// does not receive the shell's terminal signals.
func applySysProcAttr(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
}
