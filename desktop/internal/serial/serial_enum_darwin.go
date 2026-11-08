//go:build darwin && !cgo

package serial

import (
	"path/filepath"
)

// defaultListPorts on darwin without cgo cannot use the IOKit-backed
// enumerator, so it lists /dev/cu.* and /dev/tty.usb* by name only.
func defaultListPorts() ([]PortInfo, error) {
	var out []PortInfo
	for _, pat := range []string{"/dev/cu.*", "/dev/tty.usb*"} {
		matches, err := filepath.Glob(pat)
		if err != nil {
			continue
		}
		for _, m := range matches {
			out = append(out, PortInfo{Path: m, Label: filepath.Base(m)})
		}
	}
	return out, nil
}
