//go:build darwin

package system

import (
	"os"
	"os/exec"
	"strconv"
	"sync"
)

func curPid() int { return os.Getpid() }

type darwinPowerSaveBlocker struct {
	mu     sync.Mutex
	cmd    *exec.Cmd
	active bool
}

func newDarwinPowerSaveBlocker() PowerSaveBlocker {
	return &darwinPowerSaveBlocker{}
}

func (b *darwinPowerSaveBlocker) Start() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.active {
		return true
	}
	// caffeinate -i asserts idle-sleep prevention; -w ties it to this pid so
	// it exits with the shell even if we fail to stop it.
	cmd := exec.Command("caffeinate", "-i", "-w", strconv.Itoa(curPid()))
	if err := cmd.Start(); err != nil {
		return false
	}
	// Reap caffeinate when it exits (Stop kills it, or it dies with us via -w)
	// so it never lingers as a zombie.
	go func() { _ = cmd.Wait() }()
	b.cmd = cmd
	b.active = true
	return true
}

func (b *darwinPowerSaveBlocker) Stop() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if !b.active {
		return false
	}
	if b.cmd != nil && b.cmd.Process != nil {
		_ = b.cmd.Process.Kill()
	}
	b.cmd = nil
	b.active = false
	return true
}

func (b *darwinPowerSaveBlocker) Active() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.active
}

func NewPowerSaveBlocker() PowerSaveBlocker {
	return newDarwinPowerSaveBlocker()
}
