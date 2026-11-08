//go:build windows

package system

import (
	"runtime"
	"sync"

	"golang.org/x/sys/windows"
)

const (
	esContinuous       = 0x80000000
	esSystemRequired   = 0x00000001
	esDisplayRequired  = 0x00000002
	esAwayModeRequired = 0x00000040
)

type windowsPowerSaveBlocker struct {
	mu     sync.Mutex
	active bool
	once   sync.Once
	execCh chan func()
}

func newWindowsPowerSaveBlocker() PowerSaveBlocker {
	return &windowsPowerSaveBlocker{execCh: make(chan func())}
}

var procSetThreadExecutionState = windows.NewLazySystemDLL("kernel32.dll").NewProc("SetThreadExecutionState")

func setThreadExecutionState(flags uint32) uint32 {
	r, _, _ := procSetThreadExecutionState.Call(uintptr(flags))
	return uint32(r)
}

// startExecutor launches (once) a goroutine pinned to its own OS thread.
// SetThreadExecutionState is per-thread: ES_CONTINUOUS state set on one
// thread is invisible to — and cannot be cleared from — any other thread, so
// every call must run on this single dedicated thread.
func (b *windowsPowerSaveBlocker) startExecutor() {
	b.once.Do(func() {
		go func() {
			runtime.LockOSThread()
			for fn := range b.execCh {
				fn()
			}
		}()
	})
}

// setState runs setThreadExecutionState on the dedicated thread and returns
// the previous execution state (0 on failure).
func (b *windowsPowerSaveBlocker) setState(flags uint32) uint32 {
	var prev uint32
	done := make(chan struct{})
	b.execCh <- func() {
		prev = setThreadExecutionState(flags)
		close(done)
	}
	<-done
	return prev
}

func (b *windowsPowerSaveBlocker) Start() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.active {
		return true
	}
	b.startExecutor()
	prev := b.setState(esContinuous | esSystemRequired | esDisplayRequired | esAwayModeRequired)
	if prev == 0 {
		return false
	}
	b.active = true
	return true
}

func (b *windowsPowerSaveBlocker) Stop() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if !b.active {
		return false
	}
	// ES_CONTINUOUS alone clears the requirement flags on the owning thread.
	b.setState(esContinuous)
	b.active = false
	return true
}

func (b *windowsPowerSaveBlocker) Active() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.active
}

func NewPowerSaveBlocker() PowerSaveBlocker {
	return newWindowsPowerSaveBlocker()
}
