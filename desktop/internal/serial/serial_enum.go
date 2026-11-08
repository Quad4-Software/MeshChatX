//go:build cgo || !darwin

package serial

import (
	"strconv"
	"strings"

	goserial "go.bug.st/serial"
	"go.bug.st/serial/enumerator"
)

// ---- platform enumeration ---------------------------------------------------

func defaultListPorts() ([]PortInfo, error) {
	if details, err := enumerator.GetDetailedPortsList(); err == nil && len(details) > 0 {
		out := make([]PortInfo, 0, len(details))
		for _, d := range details {
			out = append(out, infoFromDetails(d))
		}
		return out, nil
	}
	names, err := goserial.GetPortsList()
	if err != nil {
		return nil, err
	}
	out := make([]PortInfo, 0, len(names))
	for _, n := range names {
		out = append(out, PortInfo{Path: n, Label: n})
	}
	return out, nil
}

func infoFromDetails(d *enumerator.PortDetails) PortInfo {
	info := PortInfo{
		Path:         d.Name,
		Label:        d.Name,
		IsUSB:        d.IsUSB,
		SerialNumber: d.SerialNumber,
	}
	if d.Manufacturer != "" || d.Product != "" {
		info.Label = strings.TrimSpace(d.Manufacturer + " " + d.Product)
	}
	if d.VID != "" {
		if v, err := strconv.ParseUint(strings.TrimPrefix(d.VID, "0x"), 16, 32); err == nil {
			iv := int(v)
			info.USBVendorId = &iv
		}
	}
	if d.PID != "" {
		if v, err := strconv.ParseUint(strings.TrimPrefix(d.PID, "0x"), 16, 32); err == nil {
			ip := int(v)
			info.USBProductId = &ip
		}
	}
	return info
}
