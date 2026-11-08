//go:build windows

package backendproc

import (
	"os/exec"
	"syscall"
)

// applySysProcAttr hides the backend console window on Windows.
func applySysProcAttr(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
}
