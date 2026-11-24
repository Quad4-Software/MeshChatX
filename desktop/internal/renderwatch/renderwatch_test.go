package renderwatch

import (
	"testing"
	"time"
)

type fakeClock struct{ t time.Time }

func (c *fakeClock) now() time.Time { return c.t }
func (c *fakeClock) advance(d time.Duration) {
	c.t = c.t.Add(d)
}

func newTestWatchdog(c *fakeClock, visible, kind *bool, reloads, crashes *int) *Watchdog {
	w := New(
		func() bool { return *visible },
		func() string {
			if *kind {
				return "app"
			}
			return "loading"
		},
		func() { *reloads++ },
		func() { *crashes++ },
		nil,
	)
	w.now = c.now
	w.BeatTimeout = 60 * time.Second
	w.ReloadWindow = 5 * time.Minute
	return w
}

func TestHeartbeatKeepsAlive(t *testing.T) {
	c := &fakeClock{t: time.Now()}
	vis, kind := true, true
	reloads, crashes := 0, 0
	w := newTestWatchdog(c, &vis, &kind, &reloads, &crashes)
	w.Beat()
	for i := 0; i < 10; i++ {
		c.advance(30 * time.Second)
		w.Beat()
		w.Tick()
	}
	if reloads != 0 || crashes != 0 {
		t.Fatalf("reloads=%d crashes=%d, want 0", reloads, crashes)
	}
}

func TestHangReloadsThenCrashes(t *testing.T) {
	c := &fakeClock{t: time.Now()}
	vis, kind := true, true
	reloads, crashes := 0, 0
	w := newTestWatchdog(c, &vis, &kind, &reloads, &crashes)
	w.Beat()
	c.advance(61 * time.Second)
	w.Tick()
	if reloads != 1 || crashes != 0 {
		t.Fatalf("after first hang reloads=%d crashes=%d, want 1/0", reloads, crashes)
	}
	// Beats never resume: next evaluation escalates to crash.
	c.advance(61 * time.Second)
	w.Tick()
	if reloads != 1 || crashes != 1 {
		t.Fatalf("after second hang reloads=%d crashes=%d, want 1/1", reloads, crashes)
	}
}

func TestHiddenWindowPausesCounting(t *testing.T) {
	c := &fakeClock{t: time.Now()}
	vis, kind := true, true
	reloads, crashes := 0, 0
	w := newTestWatchdog(c, &vis, &kind, &reloads, &crashes)
	w.Beat()
	vis = false
	for i := 0; i < 20; i++ {
		c.advance(30 * time.Second)
		w.Tick()
	}
	if reloads != 0 || crashes != 0 {
		t.Fatalf("hidden: reloads=%d crashes=%d, want 0", reloads, crashes)
	}
	// Shown again: counting resumes fresh, no instant hang.
	vis = true
	c.advance(10 * time.Second)
	w.Tick()
	if reloads != 0 {
		t.Fatalf("post-show tick reloaded early: %d", reloads)
	}
	// Still no beats after the window becomes visible again -> hang.
	c.advance(61 * time.Second)
	w.Tick()
	if reloads != 1 {
		t.Fatalf("post-show hang reloads=%d, want 1", reloads)
	}
}

func TestNonAppKindPauses(t *testing.T) {
	c := &fakeClock{t: time.Now()}
	vis, kind := true, false
	reloads, crashes := 0, 0
	w := newTestWatchdog(c, &vis, &kind, &reloads, &crashes)
	w.Beat()
	for i := 0; i < 10; i++ {
		c.advance(30 * time.Second)
		w.Tick()
	}
	if reloads != 0 || crashes != 0 {
		t.Fatalf("non-app kind: reloads=%d crashes=%d, want 0", reloads, crashes)
	}
}

func TestReloadWindowExpiryAllowsSecondReload(t *testing.T) {
	c := &fakeClock{t: time.Now()}
	vis, kind := true, true
	reloads, crashes := 0, 0
	w := newTestWatchdog(c, &vis, &kind, &reloads, &crashes)
	w.Beat()
	c.advance(61 * time.Second)
	w.Tick()
	if reloads != 1 {
		t.Fatalf("first hang reloads=%d, want 1", reloads)
	}
	// Beats resume, then stop again after the reload window has passed.
	w.Beat()
	c.advance(w.ReloadWindow + 61*time.Second)
	w.Tick()
	if reloads != 2 || crashes != 0 {
		t.Fatalf("reloads=%d crashes=%d, want 2/0", reloads, crashes)
	}
}
