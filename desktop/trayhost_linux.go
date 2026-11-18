//go:build linux

package main

import (
	"context"
	"time"

	"github.com/godbus/dbus/v5"
)

// trayHostAvailable reports whether a StatusNotifier host is watching the
// session bus. Without one the icon can never appear, so hiding the window
// would orphan it. Any bus error is treated as unavailable. A private
// connection is used so the shared bus handle Wails' systray owns is not
// touched.
func trayHostAvailable() bool {
	conn, err := dbus.ConnectSessionBus()
	if err != nil {
		return false
	}
	defer conn.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	var hasOwner bool
	err = conn.BusObject().CallWithContext(
		ctx,
		"org.freedesktop.DBus.NameHasOwner",
		0,
		"org.kde.StatusNotifierWatcher",
	).Store(&hasOwner)
	return err == nil && hasOwner
}
