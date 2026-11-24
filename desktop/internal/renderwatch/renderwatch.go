// Package renderwatch detects a hung webview renderer via heartbeats posted
// by desktop-bridge.js and drives reload-then-crash recovery.
package renderwatch

import "time"

// Watchdog evaluates renderer liveness. All dependencies are injectable.
type Watchdog struct {
	now      func() time.Time
	visible  func() bool
	pageKind func() string
	reload   func()
	crash    func()
	log      func(msg string)

	BeatTimeout   time.Duration
	ReloadWindow  time.Duration
	TickPauseKind string

	lastBeat   time.Time
	lastReload time.Time
	beatSeen   bool
}

// New builds a Watchdog. visible reports whether the main window is on
// screen and interactive; pageKind is the shell's current page kind; reload
// and crash perform the recovery actions.
func New(visible func() bool, pageKind func() string, reload, crash func(), logf func(string)) *Watchdog {
	return &Watchdog{
		now:           time.Now,
		visible:       visible,
		pageKind:      pageKind,
		reload:        reload,
		crash:         crash,
		log:           logf,
		BeatTimeout:   60 * time.Second,
		ReloadWindow:  5 * time.Minute,
		TickPauseKind: "app",
		lastBeat:      time.Now(),
	}
}

// Beat records a renderer heartbeat.
func (w *Watchdog) Beat() {
	w.lastBeat = w.now()
	w.beatSeen = true
}

// Tick evaluates liveness once. While the page is not the watched kind or
// the window is hidden/minimised/tray-hidden, counting pauses (hidden pages
// throttle timers) and resumes fresh when the window becomes usable again.
func (w *Watchdog) Tick() {
	now := w.now()
	if w.pageKind() != w.TickPauseKind || !w.visible() {
		w.lastBeat = now
		return
	}
	if !w.beatSeen {
		w.lastBeat = now
		return
	}
	if now.Sub(w.lastBeat) <= w.BeatTimeout {
		return
	}
	if w.log != nil {
		w.log("renderwatch: no renderer heartbeat for " + now.Sub(w.lastBeat).Round(time.Second).String() + ", recovering")
	}
	if !w.lastReload.IsZero() && now.Sub(w.lastReload) < w.ReloadWindow {
		if w.crash != nil {
			w.crash()
		}
		return
	}
	w.lastReload = now
	if w.reload != nil {
		w.reload()
	}
}
