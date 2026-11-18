//go:build !linux

package main

// Windows and macOS always have a tray area.
func trayHostAvailable() bool {
	return true
}
