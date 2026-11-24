package bridge

import (
	"encoding/base64"
	"errors"
	"strings"
	"testing"

	goserial "go.bug.st/serial"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/serial"
)

func TestSerialWriteSizeCap(t *testing.T) {
	m := serial.NewManager(serial.Deps{
		ListPorts: func() ([]serial.PortInfo, error) {
			return []serial.PortInfo{{Path: "/dev/ttyUSB0", Label: "x"}}, nil
		},
		OpenPort: func(path string, mode *goserial.Mode) (goserial.Port, error) {
			return nil, errors.New("no port")
		},
	})
	g, err := m.GrantPort("/dev/ttyUSB0", nil)
	if err != nil {
		t.Fatal(err)
	}
	b := New(Deps{Serial: m})
	big := base64.StdEncoding.EncodeToString(make([]byte, maxSerialWriteBytes+1))
	if _, err := b.serialWrite(map[string]any{"token": g.Token, "data": big}); err == nil ||
		!strings.Contains(err.Error(), "1 MiB") {
		t.Fatalf("oversized write should fail: %v", err)
	}
	small := base64.StdEncoding.EncodeToString([]byte("hi"))
	_, err = b.serialWrite(map[string]any{"token": g.Token, "data": small})
	if err == nil || errors.Is(err, serial.ErrPortNotOpen) == false {
		t.Fatalf("in-cap write should reach the port layer, got %v", err)
	}
}
