// Package serial implements the desktop serial bridge behind the
// navigator.serial polyfill. JS never sees raw device paths: ports are only
// reachable through opaque tokens minted after the user picks a port in the
// native picker (GrantPort), and every operation requires that token.
package serial

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"sync"

	goserial "go.bug.st/serial"
)

// PortInfo describes one enumerated serial port for the picker UI and for
// getInfo(). USBVendorId/USBProductId are decimal (WebUSB-style) or nil.
type PortInfo struct {
	Path         string `json:"path"`
	Label        string `json:"label"`
	IsUSB        bool   `json:"isUsb"`
	USBVendorId  *int   `json:"usbVendorId,omitempty"`
	USBProductId *int   `json:"usbProductId,omitempty"`
	SerialNumber string `json:"serialNumber,omitempty"`
}

// Filter mirrors the Web Serial port filter subset we can honour.
type Filter struct {
	USBVendorId  *int `json:"usbVendorId,omitempty"`
	USBProductId *int `json:"usbProductId,omitempty"`
}

// OpenOptions mirrors the Web Serial SerialPort.open() options.
type OpenOptions struct {
	BaudRate    int    `json:"baudRate"`
	DataBits    int    `json:"dataBits"`
	StopBits    string `json:"stopBits"`
	Parity      string `json:"parity"`
	FlowControl string `json:"flowControl"`
}

// Signals mirrors the Web Serial SerialPort signal state.
type Signals struct {
	DTR  bool `json:"dtr"`
	RTS  bool `json:"rts"`
	CTS  bool `json:"cts"`
	DSR  bool `json:"dsr"`
	CD   bool `json:"cd"`
	Ring bool `json:"ring"`
}

const (
	inboundChunks  = 32         // bounded read buffer -> backpressure
	inboundBufSize = 4 * 1024   // bytes per port read
	maxReadBytes   = 256 * 1024 // cap per serial-read reply
	defaultBaud    = 9600
)

var (
	ErrUnknownToken = errors.New("unknown or expired serial grant")
	ErrAlreadyOpen  = errors.New("serial port is already open")
	ErrPortNotOpen  = errors.New("serial port is not open")
	ErrNoPort       = errors.New("no serial port selected")
)

// Deps are injectable for tests.
type Deps struct {
	ListPorts func() ([]PortInfo, error)
	OpenPort  func(path string, mode *goserial.Mode) (goserial.Port, error)
}

type Grant struct {
	Token string   `json:"token"`
	Port  PortInfo `json:"port"`
}

type session struct {
	token   string
	info    PortInfo
	port    goserial.Port
	emit    func(name string, payload any)
	onExit  func()
	inbound chan []byte
	closing chan struct{}
	once    sync.Once

	mu      sync.Mutex
	pending []byte
	sig     Signals
}

// Manager owns grants and open sessions.
type Manager struct {
	deps Deps

	mu       sync.Mutex
	grants   map[string]*Grant
	sessions map[string]*session
}

func NewManager(deps Deps) *Manager {
	if deps.ListPorts == nil {
		deps.ListPorts = defaultListPorts
	}
	if deps.OpenPort == nil {
		deps.OpenPort = func(path string, mode *goserial.Mode) (goserial.Port, error) {
			return goserial.Open(path, mode)
		}
	}
	return &Manager{
		deps:     deps,
		grants:   map[string]*Grant{},
		sessions: map[string]*session{},
	}
}

// ListPorts returns the currently enumerated ports.
func (m *Manager) ListPorts() ([]PortInfo, error) {
	return m.deps.ListPorts()
}

// GrantPort validates that path is a real enumerated port matching at least
// one of filters (empty filters = any port) and mints an opaque token.
// JS can only ever present this token back; raw paths are never accepted.
func (m *Manager) GrantPort(path string, filters []Filter) (*Grant, error) {
	ports, err := m.deps.ListPorts()
	if err != nil {
		return nil, err
	}
	var info *PortInfo
	for i := range ports {
		if ports[i].Path == path {
			info = &ports[i]
			break
		}
	}
	if info == nil {
		return nil, fmt.Errorf("%w: %s", ErrNoPort, path)
	}
	if len(filters) > 0 && !matchesAnyFilter(*info, filters) {
		return nil, fmt.Errorf("%w: filters do not match %s", ErrNoPort, info.Label)
	}
	token, err := newToken()
	if err != nil {
		return nil, err
	}
	g := &Grant{Token: token, Port: *info}
	m.mu.Lock()
	m.grants[token] = g
	m.mu.Unlock()
	return g, nil
}

func matchesAnyFilter(info PortInfo, filters []Filter) bool {
	for _, f := range filters {
		if f.USBVendorId != nil && (info.USBVendorId == nil || *info.USBVendorId != *f.USBVendorId) {
			continue
		}
		if f.USBProductId != nil && (info.USBProductId == nil || *info.USBProductId != *f.USBProductId) {
			continue
		}
		return true
	}
	return false
}

func newToken() (string, error) {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(b[:]), nil
}

// RevokeGrant drops a grant and closes any session using it.
func (m *Manager) RevokeGrant(token string) {
	m.mu.Lock()
	delete(m.grants, token)
	s := m.sessions[token]
	delete(m.sessions, token)
	m.mu.Unlock()
	if s != nil {
		s.close()
	}
}

// Open opens a granted port. emit receives "serial-data" notifications.
func (m *Manager) Open(token string, opts OpenOptions, emit func(name string, payload any)) error {
	m.mu.Lock()
	g, ok := m.grants[token]
	if !ok {
		m.mu.Unlock()
		return ErrUnknownToken
	}
	if _, open := m.sessions[token]; open {
		m.mu.Unlock()
		return ErrAlreadyOpen
	}
	m.mu.Unlock()

	mode := modeFromOptions(opts)
	port, err := m.deps.OpenPort(g.Port.Path, mode)
	if err != nil {
		return err
	}

	s := &session{
		token:   token,
		info:    g.Port,
		port:    port,
		emit:    emit,
		inbound: make(chan []byte, inboundChunks),
		closing: make(chan struct{}),
	}
	s.onExit = func() {
		m.mu.Lock()
		if m.sessions[token] == s {
			delete(m.sessions, token)
		}
		m.mu.Unlock()
		// Nudge the JS side so a pending read observes the dead session.
		if s.emit != nil {
			s.emit("serial-data", map[string]any{"token": token, "closed": true})
		}
	}
	// Track the output modem bits we set so getSignals can report them.
	s.sig.DTR = true
	s.sig.RTS = true

	// Revalidate under the lock: the grant may have been revoked (or another
	// Open may have registered a session) while OpenPort was in flight.
	m.mu.Lock()
	if _, granted := m.grants[token]; !granted {
		m.mu.Unlock()
		_ = port.Close()
		return ErrUnknownToken
	}
	if _, open := m.sessions[token]; open {
		m.mu.Unlock()
		_ = port.Close()
		return ErrAlreadyOpen
	}
	m.sessions[token] = s
	m.mu.Unlock()
	go s.readLoop()
	return nil
}

func modeFromOptions(opts OpenOptions) *goserial.Mode {
	baud := opts.BaudRate
	if baud <= 0 {
		baud = defaultBaud
	}
	mode := &goserial.Mode{BaudRate: baud}
	if opts.DataBits >= 5 && opts.DataBits <= 8 {
		mode.DataBits = opts.DataBits
	}
	switch strings.ToLower(opts.Parity) {
	case "even":
		mode.Parity = goserial.EvenParity
	case "odd":
		mode.Parity = goserial.OddParity
	case "mark":
		mode.Parity = goserial.MarkParity
	case "space":
		mode.Parity = goserial.SpaceParity
	default:
		mode.Parity = goserial.NoParity
	}
	switch strings.ToLower(opts.StopBits) {
	case "onepointfive", "1.5":
		mode.StopBits = goserial.OnePointFiveStopBits
	case "two", "2":
		mode.StopBits = goserial.TwoStopBits
	default:
		mode.StopBits = goserial.OneStopBit
	}
	return mode
}

func (s *session) readLoop() {
	defer func() {
		if s.onExit != nil {
			s.onExit()
		}
	}()
	buf := make([]byte, inboundBufSize)
	for {
		n, err := s.port.Read(buf)
		if err != nil {
			return
		}
		if n <= 0 {
			continue
		}
		chunk := make([]byte, n)
		copy(chunk, buf[:n])
		select {
		case s.inbound <- chunk:
			if s.emit != nil {
				s.emit("serial-data", map[string]any{"token": s.token})
			}
		case <-s.closing:
			return
		}
	}
}

func (s *session) close() {
	s.once.Do(func() {
		close(s.closing)
		_ = s.port.Close()
	})
}

func (m *Manager) session(token string) (*session, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	s, ok := m.sessions[token]
	if !ok {
		return nil, ErrPortNotOpen
	}
	return s, nil
}

// Read drains up to maxBytes of buffered inbound data (non-blocking).
func (m *Manager) Read(token string, maxBytes int) ([]byte, error) {
	s, err := m.session(token)
	if err != nil {
		return nil, err
	}
	if maxBytes <= 0 || maxBytes > maxReadBytes {
		maxBytes = maxReadBytes
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	// Move queued chunks into pending, then slice out what was asked for.
	for len(s.pending) < maxBytes {
		select {
		case chunk := <-s.inbound:
			s.pending = append(s.pending, chunk...)
		default:
			goto drain
		}
	}
drain:
	if len(s.pending) == 0 {
		return []byte{}, nil
	}
	n := maxBytes
	if len(s.pending) < n {
		n = len(s.pending)
	}
	out := make([]byte, n)
	copy(out, s.pending[:n])
	s.pending = s.pending[n:]
	if len(s.pending) == 0 {
		s.pending = nil
	}
	return out, nil
}

// Write sends bytes to the port.
func (m *Manager) Write(token string, data []byte) (int, error) {
	s, err := m.session(token)
	if err != nil {
		return 0, err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.port.Write(data)
}

// Close closes the session but keeps the grant (port may be reopened).
func (m *Manager) Close(token string) {
	m.mu.Lock()
	s := m.sessions[token]
	delete(m.sessions, token)
	m.mu.Unlock()
	if s != nil {
		s.close()
	}
}

// SetSignals drives DTR/RTS and records the output state.
func (m *Manager) SetSignals(token string, dtr, rts *bool) error {
	s, err := m.session(token)
	if err != nil {
		return err
	}
	if dtr != nil {
		if err := s.port.SetDTR(*dtr); err != nil {
			return err
		}
		s.mu.Lock()
		s.sig.DTR = *dtr
		s.mu.Unlock()
	}
	if rts != nil {
		if err := s.port.SetRTS(*rts); err != nil {
			return err
		}
		s.mu.Lock()
		s.sig.RTS = *rts
		s.mu.Unlock()
	}
	return nil
}

// GetSignals returns modem input bits plus the tracked output state.
func (m *Manager) GetSignals(token string) (Signals, error) {
	s, err := m.session(token)
	if err != nil {
		return Signals{}, err
	}
	out := Signals{}
	s.mu.Lock()
	out.DTR, out.RTS = s.sig.DTR, s.sig.RTS
	s.mu.Unlock()
	if bits, err := s.port.GetModemStatusBits(); err == nil && bits != nil {
		out.CTS = bits.CTS
		out.DSR = bits.DSR
		out.CD = bits.DCD
		out.Ring = bits.RI
	}
	return out, nil
}

// GetInfo returns the granted port's USB identity.
func (m *Manager) GetInfo(token string) (PortInfo, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if s, ok := m.sessions[token]; ok {
		return s.info, nil
	}
	if g, ok := m.grants[token]; ok {
		return g.Port, nil
	}
	return PortInfo{}, ErrUnknownToken
}

// GrantedPorts lists grants (for getPorts()-style UIs).
func (m *Manager) GrantedPorts() []Grant {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]Grant, 0, len(m.grants))
	for _, g := range m.grants {
		out = append(out, *g)
	}
	return out
}

// CloseAll shuts down every session (app quit).
func (m *Manager) CloseAll() {
	m.mu.Lock()
	sessions := make([]*session, 0, len(m.sessions))
	for _, s := range m.sessions {
		sessions = append(sessions, s)
	}
	m.sessions = map[string]*session{}
	m.mu.Unlock()
	for _, s := range sessions {
		s.close()
	}
}
