//go:build windows

package system

import (
	"syscall"
	"unsafe"
)

var procGetSystemPowerStatus = syscall.NewLazyDLL("kernel32.dll").NewProc("GetSystemPowerStatus")

type systemPowerStatus struct {
	ACLineStatus        byte
	BatteryFlag         byte
	BatteryLifePercent  byte
	SystemStatusFlag    byte
	BatteryLifeTime     uint32
	BatteryFullLifeTime uint32
}

// onBatteryPower uses GetSystemPowerStatus.
func onBatteryPower() (bool, bool) {
	var s systemPowerStatus
	if r, _, _ := procGetSystemPowerStatus.Call(uintptr(unsafe.Pointer(&s))); r == 0 {
		return false, false
	}
	// ACLineStatus: 0 = offline (battery), 1 = online (AC), 255 = unknown.
	if s.ACLineStatus == 255 {
		return false, false
	}
	return s.ACLineStatus == 0, true
}
