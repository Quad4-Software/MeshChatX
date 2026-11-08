//go:build darwin

package system

import (
	"os/exec"
	"strings"
)

// onBatteryPower parses `pmset -g batt` for "Now drawing from 'Battery Power'".
func onBatteryPower() (bool, bool) {
	out, err := exec.Command("pmset", "-g", "batt").Output()
	if err != nil {
		return false, false
	}
	text := string(out)
	if strings.Contains(text, "Battery Power") && strings.Contains(text, "Now drawing from 'Battery Power'") {
		return true, true
	}
	if strings.Contains(text, "AC Power") {
		return false, true
	}
	return false, false
}
