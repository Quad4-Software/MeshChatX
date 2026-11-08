package serial

import (
	"bufio"
	"errors"
	"io"
	"os"
	"os/exec"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	goserial "go.bug.st/serial"
)

type fakePort struct {
	mu       sync.Mutex
	readCh   chan []byte
	written  [][]byte
	closed   bool
	dtr, rts bool
	bits     *goserial.ModemStatusBits
}

func newFakePort() *fakePort {
	return &fakePort{readCh: make(chan []byte, 16), bits: &goserial.ModemStatusBits{}}
}

func (f *fakePort) push(b []byte) { f.readCh <- b }

func (f *fakePort) SetMode(*goserial.Mode) error { return nil }
func (f *fakePort) Read(p []byte) (int, error) {
	b, ok := <-f.readCh
	if !ok {
		return 0, io.EOF
	}
	return copy(p, b), nil
}
func (f *fakePort) Write(p []byte) (int, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.closed {
		return 0, errors.New("closed")
	}
	cp := append([]byte(nil), p...)
	f.written = append(f.written, cp)
	return len(p), nil
}
func (f *fakePort) Drain() error             { return nil }
func (f *fakePort) ResetInputBuffer() error  { return nil }
func (f *fakePort) ResetOutputBuffer() error { return nil }
func (f *fakePort) SetDTR(v bool) error      { f.dtr = v; return nil }
func (f *fakePort) SetRTS(v bool) error      { f.rts = v; return nil }
func (f *fakePort) GetModemStatusBits() (*goserial.ModemStatusBits, error) {
	return f.bits, nil
}
func (f *fakePort) SetReadTimeout(time.Duration) error { return nil }
func (f *fakePort) Close() error {
	f.mu.Lock()
	if f.closed {
		f.mu.Unlock()
		return nil
	}
	f.closed = true
	f.mu.Unlock()
	close(f.readCh)
	return nil
}
func (f *fakePort) Break(time.Duration) error { return nil }

func (f *fakePort) writes() [][]byte {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([][]byte(nil), f.written...)
}

func vid(v int) *int { return &v }
func testPorts() []PortInfo {
	return []PortInfo{
		{Path: "/dev/ttyUSB0", Label: "CP2102", IsUSB: true, USBVendorId: vid(0x10c4), USBProductId: vid(0xea60)},
		{Path: "/dev/ttyACM0", Label: "nRF52", IsUSB: true, USBVendorId: vid(0x1915), USBProductId: vid(0x520a)},
		{Path: "/dev/ttyS0", Label: "/dev/ttyS0"},
	}
}

func newTestManager(port *fakePort) *Manager {
	return NewManager(Deps{
		ListPorts: func() ([]PortInfo, error) { return testPorts(), nil },
		OpenPort: func(path string, mode *goserial.Mode) (goserial.Port, error) {
			if path != "/dev/ttyUSB0" && path != "/dev/ttyACM0" && path != "/dev/ttyS0" {
				return nil, errors.New("bad path")
			}
			return port, nil
		},
	})
}

func TestGrantPort(t *testing.T) {
	m := newTestManager(newFakePort())
	g, err := m.GrantPort("/dev/ttyUSB0", nil)
	if err != nil {
		t.Fatal(err)
	}
	if g.Token == "" || len(g.Token) != 32 {
		t.Fatalf("token: %q", g.Token)
	}
	if g.Port.Path != "/dev/ttyUSB0" || g.Port.USBVendorId == nil || *g.Port.USBVendorId != 0x10c4 {
		t.Fatalf("port info: %+v", g.Port)
	}

	// unknown path rejected
	if _, err := m.GrantPort("/dev/ttyFAKE9", nil); err == nil {
		t.Fatal("expected error for unknown path")
	}
	// filter mismatch rejected
	if _, err := m.GrantPort("/dev/ttyUSB0", []Filter{{USBVendorId: vid(0x1234)}}); err == nil {
		t.Fatal("expected filter mismatch error")
	}
	// filter match accepted
	if _, err := m.GrantPort("/dev/ttyACM0", []Filter{{USBVendorId: vid(0x1915), USBProductId: vid(0x520a)}}); err != nil {
		t.Fatal(err)
	}
	// non-USB port has nil ids -> vendor filter must not match
	if _, err := m.GrantPort("/dev/ttyS0", []Filter{{USBVendorId: vid(0x10c4)}}); err == nil {
		t.Fatal("expected non-USB port to fail vendor filter")
	}
}

func TestOpenGrantEnforcement(t *testing.T) {
	m := newTestManager(newFakePort())
	// no grant -> cannot open even with a plausible-looking token
	if err := m.Open("deadbeef", OpenOptions{BaudRate: 115200}, nil); !errors.Is(err, ErrUnknownToken) {
		t.Fatalf("expected ErrUnknownToken, got %v", err)
	}
	g, _ := m.GrantPort("/dev/ttyUSB0", nil)
	if err := m.Open(g.Token, OpenOptions{BaudRate: 115200}, nil); err != nil {
		t.Fatal(err)
	}
	if err := m.Open(g.Token, OpenOptions{}, nil); !errors.Is(err, ErrAlreadyOpen) {
		t.Fatalf("expected ErrAlreadyOpen, got %v", err)
	}
	m.Close(g.Token)
	// reopen after close works
	if err := m.Open(g.Token, OpenOptions{}, nil); err != nil {
		t.Fatal(err)
	}
	m.CloseAll()
}

func TestReadWriteSignals(t *testing.T) {
	port := newFakePort()
	m := newTestManager(port)
	events := make(chan string, 16)
	g, _ := m.GrantPort("/dev/ttyACM0", nil)
	if err := m.Open(g.Token, OpenOptions{BaudRate: 115200}, func(name string, payload any) {
		events <- name
	}); err != nil {
		t.Fatal(err)
	}

	// write
	if n, err := m.Write(g.Token, []byte("PING")); err != nil || n != 4 {
		t.Fatalf("write: %d %v", n, err)
	}
	w := port.writes()
	if len(w) != 1 || string(w[0]) != "PING" {
		t.Fatalf("port writes: %q", w)
	}

	// inbound data -> read
	port.push([]byte("PONG"))
	deadline := time.Now().Add(2 * time.Second)
	var got []byte
	for time.Now().Before(deadline) {
		got, _ = m.Read(g.Token, 1024)
		if len(got) > 0 {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if string(got) != "PONG" {
		t.Fatalf("read: %q", got)
	}
	// serial-data event emitted
	select {
	case e := <-events:
		if e != "serial-data" {
			t.Fatalf("event: %q", e)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("expected serial-data event")
	}

	// signals
	tru := true
	fls := false
	if err := m.SetSignals(g.Token, &tru, &fls); err != nil {
		t.Fatal(err)
	}
	sig, err := m.GetSignals(g.Token)
	if err != nil {
		t.Fatal(err)
	}
	if !sig.DTR || sig.RTS {
		t.Fatalf("signals: %+v", sig)
	}

	// info via grant and session
	info, err := m.GetInfo(g.Token)
	if err != nil || info.Path != "/dev/ttyACM0" {
		t.Fatalf("info: %+v %v", info, err)
	}

	// forget revokes grant + closes session
	m.RevokeGrant(g.Token)
	if _, err := m.Read(g.Token, 1); !errors.Is(err, ErrPortNotOpen) {
		t.Fatalf("expected ErrPortNotOpen after forget, got %v", err)
	}
	if err := m.Open(g.Token, OpenOptions{}, nil); !errors.Is(err, ErrUnknownToken) {
		t.Fatalf("expected ErrUnknownToken after forget, got %v", err)
	}
}

// TestOpenRevalidatesGrant covers the TOCTOU window: the grant is revoked
// while OpenPort is in flight, so Open must fail and close the port rather
// than registering a session on a dead grant.
func TestOpenRevalidatesGrant(t *testing.T) {
	port := newFakePort()
	var m *Manager
	var token string
	m = NewManager(Deps{
		ListPorts: func() ([]PortInfo, error) { return testPorts(), nil },
		OpenPort: func(path string, mode *goserial.Mode) (goserial.Port, error) {
			m.RevokeGrant(token)
			return port, nil
		},
	})
	g, err := m.GrantPort("/dev/ttyUSB0", nil)
	if err != nil {
		t.Fatal(err)
	}
	token = g.Token
	if err := m.Open(token, OpenOptions{}, nil); !errors.Is(err, ErrUnknownToken) {
		t.Fatalf("expected ErrUnknownToken after revoke-during-open, got %v", err)
	}
	port.mu.Lock()
	closed := port.closed
	port.mu.Unlock()
	if !closed {
		t.Fatal("port opened on revoked grant was not closed")
	}
}

// TestOpenConcurrentSingleWinner: two Opens racing through OpenPort must not
// both register a session; the loser gets ErrAlreadyOpen and its port closed.
func TestOpenConcurrentSingleWinner(t *testing.T) {
	port1, port2 := newFakePort(), newFakePort()
	var calls int32
	firstEntered := make(chan struct{})
	releaseFirst := make(chan struct{})
	m := NewManager(Deps{
		ListPorts: func() ([]PortInfo, error) { return testPorts(), nil },
		OpenPort: func(path string, mode *goserial.Mode) (goserial.Port, error) {
			if atomic.AddInt32(&calls, 1) == 1 {
				close(firstEntered)
				<-releaseFirst
				return port1, nil
			}
			return port2, nil
		},
	})
	g, err := m.GrantPort("/dev/ttyUSB0", nil)
	if err != nil {
		t.Fatal(err)
	}
	errCh := make(chan error, 1)
	go func() { errCh <- m.Open(g.Token, OpenOptions{}, nil) }()
	<-firstEntered
	// Second open runs to completion while the first is still inside OpenPort.
	if err := m.Open(g.Token, OpenOptions{}, nil); err != nil {
		t.Fatalf("second open should win: %v", err)
	}
	close(releaseFirst)
	if err := <-errCh; !errors.Is(err, ErrAlreadyOpen) {
		t.Fatalf("first open should lose with ErrAlreadyOpen, got %v", err)
	}
	port1.mu.Lock()
	closed := port1.closed
	port1.mu.Unlock()
	if !closed {
		t.Fatal("losing port was not closed")
	}
	m.CloseAll()
}

func TestReadBackpressureBounded(t *testing.T) {
	port := newFakePort()
	m := newTestManager(port)
	g, _ := m.GrantPort("/dev/ttyS0", nil)
	if err := m.Open(g.Token, OpenOptions{}, nil); err != nil {
		t.Fatal(err)
	}
	// flood more than inboundChunks*buf without reading
	for i := 0; i < inboundChunks+8; i++ {
		port.push([]byte("x"))
	}
	// reader goroutine blocks once inbound is full; give it a moment
	time.Sleep(100 * time.Millisecond)
	// drain everything; must not deadlock or lose the session
	total := 0
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) && total < inboundChunks+8 {
		b, err := m.Read(g.Token, 65536)
		if err == nil {
			total += len(b)
		}
		time.Sleep(5 * time.Millisecond)
	}
	if total != inboundChunks+8 {
		t.Fatalf("drained %d of %d bytes", total, inboundChunks+8)
	}
	m.CloseAll()
}

// TestPTYRoundTrip proves real byte round-trip through go.bug.st/serial on a
// kernel pty pair (python3 pty helper echoes uppercased bytes back).
func TestPTYRoundTrip(t *testing.T) {
	if _, err := exec.LookPath("python3"); err != nil {
		t.Skip("python3 unavailable")
	}
	if _, err := os.Stat("/dev/ptmx"); err != nil {
		t.Skip("no /dev/ptmx")
	}
	const helper = `
import os, pty, sys
m, s = pty.openpty()
sys.stdout.write(os.ttyname(s) + "\n")
sys.stdout.flush()
while True:
    try:
        data = os.read(m, 4096)
    except OSError:
        break
    if not data:
        break
    os.write(m, data.upper())
`
	cmd := exec.Command("python3", "-c", helper)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = cmd.Process.Kill(); _ = cmd.Wait() }()

	line, err := bufio.NewReader(stdout).ReadString('\n')
	if err != nil {
		t.Fatal(err)
	}
	slave := strings.TrimSpace(line)
	if !strings.HasPrefix(slave, "/dev/pts/") {
		t.Fatalf("unexpected pty slave: %q", slave)
	}

	port, err := goserial.Open(slave, &goserial.Mode{BaudRate: 115200})
	if err != nil {
		t.Skipf("cannot open pty slave with serial lib: %v", err)
	}
	defer port.Close()

	msg := []byte("meshchatx-pty-probe")
	if _, err := port.Write(msg); err != nil {
		t.Fatal(err)
	}
	want := strings.ToUpper(string(msg))
	buf := make([]byte, len(want))
	deadline := time.Now().Add(5 * time.Second)
	got := 0
	for got < len(buf) && time.Now().Before(deadline) {
		if err := port.SetReadTimeout(500 * time.Millisecond); err != nil {
			t.Fatal(err)
		}
		n, err := port.Read(buf[got:])
		if err == nil {
			got += n
		}
	}
	if string(buf) != want {
		t.Fatalf("pty round-trip: got %q want %q", buf, want)
	}
}

func TestModeFromOptions(t *testing.T) {
	mode := modeFromOptions(OpenOptions{BaudRate: 115200, DataBits: 7, Parity: "even", StopBits: "two"})
	if mode.BaudRate != 115200 || mode.DataBits != 7 || mode.Parity != goserial.EvenParity || mode.StopBits != goserial.TwoStopBits {
		t.Fatalf("mode: %+v", mode)
	}
	def := modeFromOptions(OpenOptions{})
	if def.BaudRate != defaultBaud || def.Parity != goserial.NoParity || def.StopBits != goserial.OneStopBit {
		t.Fatalf("default mode: %+v", def)
	}
}
