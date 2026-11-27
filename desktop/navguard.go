package main

import (
	"log"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/bridge"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/renderwatch"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/security"
)

const (
	navCheckDelay    = 5 * time.Second
	navRetryDelay    = 5 * time.Second
	navEnforceWindow = 10 * time.Second
	navMaxEnforces   = 3
)

type navPending struct {
	since   time.Time
	retried bool
	seq     uint64
}

// navGuard enforces in-window navigation policy after each page finishes
// loading. Wails 3.1.0 has no pre-navigation hook, so enforcement is
// post-hoc: the bridge reports the loaded page's URL; a page without the
// bridge (foreign origin) reports nothing and is treated as untrusted.
type navGuard struct {
	mu        sync.Mutex
	now       func() time.Time
	schedule  func(d time.Duration, f func()) func()
	report    func(id uint) (bridge.PageReport, bool)
	isChild   func(id uint) bool
	closeByID func(id uint)
	setMain   func(rawurl string)
	openExt   func(rawurl string)
	crash     func()
	log       func(msg string)

	fallback string
	lastGood string
	seq      uint64
	seqByID  map[uint]uint64
	pending  map[uint]navPending
	cancels  map[uint]func()
	enf      map[uint][]time.Time
}

func newNavGuard(fallback string) *navGuard {
	g := &navGuard{
		now:      time.Now,
		fallback: fallback,
		lastGood: fallback,
		seqByID:  map[uint]uint64{},
		pending:  map[uint]navPending{},
		cancels:  map[uint]func(){},
		enf:      map[uint][]time.Time{},
	}
	g.schedule = func(d time.Duration, f func()) func() {
		t := time.AfterFunc(d, f)
		return func() { t.Stop() }
	}
	return g
}

// onPageFinished arms the post-navigation check for a window. Call after
// RotateToken so the page-url report (triggered by __init) lands after the
// pending timestamp.
func (g *navGuard) onPageFinished(id uint) {
	if g == nil {
		return
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	g.seq++
	seq := g.seq
	g.seqByID[id] = seq
	g.pending[id] = navPending{since: g.now(), seq: seq}
	if c, ok := g.cancels[id]; ok {
		c()
	}
	g.cancels[id] = g.schedule(navCheckDelay, func() { g.check(id, seq) })
}

func (g *navGuard) check(id uint, seq uint64) {
	g.mu.Lock()
	p, ok := g.pending[id]
	if ok && p.seq != seq {
		ok = false
	}
	if ok {
		delete(g.pending, id)
	}
	g.mu.Unlock()
	if !ok {
		return
	}
	rep, has := g.report(id)
	fresh := has && rep.At.After(p.since)
	url := ""
	if fresh {
		url = rep.URL
	}
	child := g.isChild(id)
	action, ext := security.WindowNavDecision(url, child)
	if action == security.NavAllow {
		if fresh && !child && isRestorableURL(url) {
			g.mu.Lock()
			if g.seqByID[id] == seq {
				g.lastGood = url
			}
			g.mu.Unlock()
		}
		return
	}
	if !fresh && !p.retried {
		// No bridge report yet: the page may still be initialising. Retry
		// once before treating the load as a foreign (bridge-less) page.
		g.mu.Lock()
		if g.seqByID[id] != seq {
			g.mu.Unlock()
			return
		}
		if c, ok := g.cancels[id]; ok {
			c()
		}
		g.pending[id] = navPending{since: p.since, retried: true, seq: seq}
		g.cancels[id] = g.schedule(navRetryDelay, func() { g.check(id, seq) })
		g.mu.Unlock()
		return
	}
	g.mu.Lock()
	if g.seqByID[id] != seq {
		g.mu.Unlock()
		return
	}
	g.mu.Unlock()
	if g.log != nil {
		kind := "main"
		if child {
			kind = "child"
		}
		g.log("navguard: blocked in-window navigation to " + url + " (" + kind + ")")
	}
	g.enforce(id, child, ext)
}

// isRestorableURL limits lastGood to http(s) pages: about:blank/blob: are
// allowed navigations but useless (or impossible) restore targets.
func isRestorableURL(raw string) bool {
	u, err := url.Parse(strings.TrimSpace(raw))
	return err == nil && (u.Scheme == "http" || u.Scheme == "https")
}

func (g *navGuard) enforce(id uint, child bool, ext string) {
	g.mu.Lock()
	now := g.now()
	recent := g.enf[id][:0]
	for _, t := range g.enf[id] {
		if now.Sub(t) < navEnforceWindow {
			recent = append(recent, t)
		}
	}
	if len(recent) >= navMaxEnforces {
		g.enf[id] = recent
		g.mu.Unlock()
		if g.log != nil {
			g.log("navguard: navigation loop detected, escalating")
		}
		if child {
			g.closeByID(id)
		} else if g.crash != nil {
			g.crash()
		}
		return
	}
	g.enf[id] = append(recent, now)
	restore := g.lastGood
	if restore == "" {
		restore = g.fallback
	}
	g.mu.Unlock()
	if ext != "" && g.openExt != nil {
		g.openExt(ext)
	}
	if child {
		g.closeByID(id)
	} else if g.setMain != nil {
		g.setMain(restore)
	}
}

// ---- shellState wiring -------------------------------------------------------

// armNavGuard binds the navigation guard and the renderer watchdog. Call
// after the bridge exists and before app.Run.
func (s *shellState) armNavGuard(fallback string) {
	g := newNavGuard(fallback)
	g.report = func(id uint) (bridge.PageReport, bool) {
		w := s.windowByID(id)
		if w == nil || s.bridge == nil {
			return bridge.PageReport{}, false
		}
		return s.bridge.LastPageURL(w)
	}
	g.isChild = func(id uint) bool {
		s.mu.Lock()
		defer s.mu.Unlock()
		return s.mainWindow == nil || s.mainWindow.ID() != id
	}
	g.closeByID = func(id uint) {
		if w := s.windowByID(id); w != nil {
			w.Close()
		}
	}
	g.setMain = func(rawurl string) {
		s.navMu.Lock()
		defer s.navMu.Unlock()
		if s.mainWindow != nil {
			s.mainWindow.SetURL(rawurl)
		}
	}
	g.openExt = func(u string) { s.openExternal(u) }
	g.crash = func() {
		s.showCrashPage(map[string]any{"code": "navigation_loop"})
	}
	g.log = s.navLog
	s.navGuard = g

	s.watchdog = renderwatch.New(
		s.mainWindowUsable,
		s.getPageKind,
		func() {
			s.navMu.Lock()
			defer s.navMu.Unlock()
			if s.mainWindow != nil {
				s.mainWindow.Reload()
			}
		},
		func() {
			s.showCrashPage(map[string]any{"code": "webview_hang", "signal": "hang"})
		},
		s.navLog,
	)
	go func() {
		t := time.NewTicker(10 * time.Second)
		defer t.Stop()
		for range t.C {
			if s.watchdog != nil {
				s.watchdog.Tick()
			}
		}
	}()
}

func (s *shellState) windowByID(id uint) application.Window {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.mainWindow != nil && s.mainWindow.ID() == id {
		return s.mainWindow
	}
	for _, w := range s.childWindows {
		if w != nil && w.ID() == id {
			return w
		}
	}
	return nil
}

func (s *shellState) navLog(msg string) {
	if s.sysLog != nil {
		s.sysLog.Write(msg)
		return
	}
	log.Println(msg)
}

// mainWindowUsable reports whether the watchdog may evaluate heartbeats:
// the main window is visible, not minimised, and was not hidden to the tray
// within the last 30 s (timers throttle while hidden, so counting pauses).
func (s *shellState) mainWindowUsable() bool {
	s.mu.Lock()
	w := s.mainWindow
	hidden := s.hiddenAt
	s.mu.Unlock()
	if w == nil || !w.IsVisible() || w.IsMinimised() {
		return false
	}
	return hidden.IsZero() || time.Since(hidden) > 30*time.Second
}

func (s *shellState) noteRendererBeat(w application.Window) {
	if w == nil || s.watchdog == nil {
		return
	}
	s.mu.Lock()
	main := s.mainWindow
	s.mu.Unlock()
	if main != nil && w == main {
		s.watchdog.Beat()
	}
}
