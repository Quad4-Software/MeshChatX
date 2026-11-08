//go:build linux

package system

import (
	"os"
	"sync"

	"github.com/godbus/dbus/v5"
)

type linuxPowerSaveBlocker struct {
	mu     sync.Mutex
	conn   *dbus.Conn
	fd     dbus.UnixFD
	cookie uint32
	active bool
}

func newLinuxPowerSaveBlocker() PowerSaveBlocker {
	return &linuxPowerSaveBlocker{fd: -1}
}

var sessionBusOnce struct {
	once sync.Once
	conn *dbus.Conn
	err  error
}

func sessionBus() (*dbus.Conn, error) {
	sessionBusOnce.once.Do(func() {
		sessionBusOnce.conn, sessionBusOnce.err = dbus.ConnectSessionBus()
	})
	return sessionBusOnce.conn, sessionBusOnce.err
}

// Start inhibits idle via logind (fd-held) with a ScreenSaver fallback.
func (b *linuxPowerSaveBlocker) Start() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.active {
		return true
	}
	conn, err := sessionBus()
	if err != nil {
		return false
	}
	obj := conn.Object("org.freedesktop.login1", "/org/freedesktop/login1")
	var fd dbus.UnixFD
	call := obj.Call("org.freedesktop.login1.Manager.Inhibit", 0,
		"app", "MeshChatX", "block-idle", "ignore-inhibited")
	if call.Err == nil && len(call.Body) > 0 {
		if v, ok := call.Body[0].(dbus.UnixFD); ok {
			fd = v
			b.conn = conn
			b.fd = fd
			b.active = true
			return true
		}
	}
	// Fallback: freedesktop ScreenSaver inhibition (cookie based). It is a
	// different bus name AND object path than logind — calling it on the
	// login1 object always fails.
	ssObj := conn.Object("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver")
	var cookie uint32
	call = ssObj.Call("org.freedesktop.ScreenSaver.Inhibit", 0, "MeshChatX", "MeshChatX is running")
	if call.Err == nil && len(call.Body) > 0 {
		if v, ok := call.Body[0].(uint32); ok {
			cookie = v
			b.conn = conn
			b.cookie = cookie
			b.active = true
			return true
		}
	}
	return false
}

func (b *linuxPowerSaveBlocker) Stop() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if !b.active {
		return false
	}
	if b.conn != nil {
		if b.fd >= 0 {
			_ = os.NewFile(uintptr(b.fd), "power-save-inhibit").Close()
		} else if b.cookie != 0 {
			obj := b.conn.Object("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver")
			_ = obj.Call("org.freedesktop.ScreenSaver.UnInhibit", 0, b.cookie).Err
		}
	}
	b.fd = -1
	b.cookie = 0
	b.active = false
	return true
}

func (b *linuxPowerSaveBlocker) Active() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.active
}

func NewPowerSaveBlocker() PowerSaveBlocker {
	return newLinuxPowerSaveBlocker()
}
