//go:build linux

package system

import (
	"os"
	"path/filepath"
	"strings"
)

// onBatteryPower reports whether the machine is currently on battery, parsed
// from /sys/class/power_supply (any supply whose type is Battery/Mains).
func onBatteryPower() (bool, bool) {
	dir := "/sys/class/power_supply"
	entries, err := os.ReadDir(dir)
	if err != nil {
		return false, false
	}
	found := false
	onBattery := false
	for _, e := range entries {
		typePath := filepath.Join(dir, e.Name(), "type")
		data, err := os.ReadFile(typePath)
		if err != nil {
			continue
		}
		t := strings.TrimSpace(string(data))
		if strings.EqualFold(t, "Battery") || strings.EqualFold(t, "UPS") {
			found = true
			// A battery supply present does not prove we're unplugged; check
			// status: "Discharging" means on battery.
			statusData, err := os.ReadFile(filepath.Join(dir, e.Name(), "status"))
			if err == nil {
				status := strings.TrimSpace(string(statusData))
				if strings.EqualFold(status, "Discharging") {
					onBattery = true
				}
			}
		}
	}
	if !found {
		return false, false
	}
	return onBattery, true
}
