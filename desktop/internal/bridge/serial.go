package bridge

import (
	"encoding/base64"
	"encoding/json"
	"fmt"

	"github.com/wailsapp/wails/v3/pkg/application"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/serial"
)

// Serial bridge methods backing the navigator.serial polyfill. All port
// access is token-gated: JS can only present tokens minted by GrantPort
// after the user picked the port in the native picker.

func (b *Bridge) serialManager() (*serial.Manager, error) {
	if b.deps.Serial == nil {
		return nil, fmt.Errorf("serial bridge unavailable")
	}
	return b.deps.Serial, nil
}

func (b *Bridge) serialListPorts() (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	ports, err := m.ListPorts()
	if err != nil {
		return nil, err
	}
	return map[string]any{"ports": ports}, nil
}

func (b *Bridge) serialRequestPort(window application.Window, opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	if b.deps.PickSerialPort == nil {
		return nil, fmt.Errorf("serial picker unavailable")
	}
	filters, err := parseSerialFilters(opts)
	if err != nil {
		return nil, err
	}
	filtersJSON, _ := json.Marshal(map[string]any{"filters": filters})
	raw, ok := b.deps.PickSerialPort(string(filtersJSON))
	if !ok || raw == "" {
		return nil, nil // cancelled -> JS throws NotFoundError
	}
	var picked struct {
		Path string `json:"path"`
	}
	if err := json.Unmarshal([]byte(raw), &picked); err != nil || picked.Path == "" {
		return nil, nil
	}
	grant, err := m.GrantPort(picked.Path, filters)
	if err != nil {
		return nil, err
	}
	return map[string]any{"token": grant.Token, "port": grant.Port}, nil
}

func parseSerialFilters(opts map[string]any) ([]serial.Filter, error) {
	if opts == nil {
		return nil, nil
	}
	raw, ok := opts["filters"].([]any)
	if !ok || len(raw) == 0 {
		return nil, nil
	}
	out := make([]serial.Filter, 0, len(raw))
	for _, item := range raw {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		f := serial.Filter{}
		if v, ok := m["usbVendorId"].(float64); ok {
			iv := int(v)
			f.USBVendorId = &iv
		}
		if v, ok := m["usbProductId"].(float64); ok {
			ip := int(v)
			f.USBProductId = &ip
		}
		out = append(out, f)
	}
	return out, nil
}

func serialToken(opts map[string]any) (string, error) {
	if opts == nil {
		return "", fmt.Errorf("missing serial token")
	}
	tok, _ := opts["token"].(string)
	if tok == "" {
		return "", fmt.Errorf("missing serial token")
	}
	return tok, nil
}

func (b *Bridge) serialOpen(window application.Window, opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	options := serial.OpenOptions{}
	if v, ok := opts["baudRate"].(float64); ok {
		options.BaudRate = int(v)
	}
	if v, ok := opts["dataBits"].(float64); ok {
		options.DataBits = int(v)
	}
	options.StopBits, _ = opts["stopBits"].(string)
	options.Parity, _ = opts["parity"].(string)
	options.FlowControl, _ = opts["flowControl"].(string)

	emit := func(name string, payload any) { b.Emit(window, name, payload) }
	if err := m.Open(token, options, emit); err != nil {
		return nil, err
	}
	return map[string]any{"ok": true}, nil
}

func (b *Bridge) serialRead(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	maxBytes := 0
	if v, ok := opts["maxBytes"].(float64); ok {
		maxBytes = int(v)
	}
	data, err := m.Read(token, maxBytes)
	if err != nil {
		return nil, err
	}
	return map[string]any{"data": base64.StdEncoding.EncodeToString(data)}, nil
}

func (b *Bridge) serialWrite(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	encoded, _ := opts["data"].(string)
	data, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 serial data")
	}
	n, err := m.Write(token, data)
	if err != nil {
		return nil, err
	}
	return map[string]any{"written": n}, nil
}

func (b *Bridge) serialClose(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	m.Close(token)
	return map[string]any{"ok": true}, nil
}

func boolPtrArg(opts map[string]any, key string) *bool {
	if opts == nil {
		return nil
	}
	if v, ok := opts[key].(bool); ok {
		return &v
	}
	return nil
}

func (b *Bridge) serialSetSignals(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	if err := m.SetSignals(token, boolPtrArg(opts, "dtr"), boolPtrArg(opts, "rts")); err != nil {
		return nil, err
	}
	return map[string]any{"ok": true}, nil
}

func (b *Bridge) serialGetSignals(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	sig, err := m.GetSignals(token)
	if err != nil {
		return nil, err
	}
	return sig, nil
}

func (b *Bridge) serialGetInfo(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	info, err := m.GetInfo(token)
	if err != nil {
		return nil, err
	}
	return info, nil
}

func (b *Bridge) serialForget(opts map[string]any) (any, error) {
	m, err := b.serialManager()
	if err != nil {
		return nil, err
	}
	token, err := serialToken(opts)
	if err != nil {
		return nil, err
	}
	m.RevokeGrant(token)
	return map[string]any{"ok": true}, nil
}
