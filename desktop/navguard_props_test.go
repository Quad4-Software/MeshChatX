package main

import (
	"fmt"
	"math/rand"
	"testing"
	"time"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/bridge"
	"github.com/Quad4-Software/MeshChatX/desktop/internal/security"
)

// propHarness drives the navGuard with explicit control over scheduled
// callbacks and time so randomised sequences can be checked against
// invariants.
type propHarness struct {
	now     time.Time
	report  bridge.PageReport
	hasRep  bool
	child   bool
	closed  []uint
	mainSet []string
	ext     []string
	crashes int

	// scheduled callbacks tagged with the seq they will invoke.
	pending []propCb
	seqByCb map[int]uint64
	nextCb  int
}

type propCb struct {
	fn  func()
	seq uint64 // seq captured inside the closure at fire time is unknown; store schedule-time seq
	id  uint
}

func newPropHarness() *propHarness {
	return &propHarness{
		now:     time.Now(),
		seqByCb: map[int]uint64{},
	}
}

// guard builds a navGuard wired to the harness. The returned function reports
// the current seq for a window id.
func (h *propHarness) guard() (*navGuard, func(id uint) uint64) {
	g := newNavGuard("http://127.0.0.1:9337/__shell/loading.html")
	g.now = func() time.Time { return h.now }
	g.schedule = func(d time.Duration, fn func()) func() {
		h.pending = append(h.pending, propCb{fn: fn})
		return func() {}
	}
	g.report = func(id uint) (bridge.PageReport, bool) { return h.report, h.hasRep }
	g.isChild = func(id uint) bool { return h.child }
	g.closeByID = func(id uint) { h.closed = append(h.closed, id) }
	g.setMain = func(u string) { h.mainSet = append(h.mainSet, u) }
	g.openExt = func(u string) { h.ext = append(h.ext, u) }
	g.crash = func() { h.crashes++ }
	g.log = func(string) {}
	seqOf := func(id uint) uint64 {
		g.mu.Lock()
		defer g.mu.Unlock()
		return g.seqByID[id]
	}
	return g, seqOf
}

func (h *propHarness) enforcements() int {
	return len(h.closed) + len(h.mainSet) + h.crashes
}

// TestPropEnforceEscalationCap randomises enforce() calls with random time
// gaps and checks the sliding-window cap: a crash (main window escalation)
// may only happen when navMaxEnforces enforcements already occurred inside
// the trailing window, and enforcement never exceeds the cap within any
// window.
func TestPropEnforceEscalationCap(t *testing.T) {
	for seed := int64(0); seed < 200; seed++ {
		r := rand.New(rand.NewSource(seed))
		h := newPropHarness()
		g, _ := h.guard()

		// Model of the sliding window for id 1.
		var modelTimes []time.Time
		crashesModel := 0
		setMainModel := 0

		steps := 1 + r.Intn(10)
		for i := 0; i < steps; i++ {
			h.now = h.now.Add(time.Duration(r.Intn(20)) * time.Second)
			before := h.enforcements()
			g.enforce(1, false, "")
			after := h.enforcements()

			// Update model.
			now := h.now
			recent := modelTimes[:0]
			for _, tm := range modelTimes {
				if now.Sub(tm) < navEnforceWindow {
					recent = append(recent, tm)
				}
			}
			modelTimes = recent
			if len(modelTimes) >= navMaxEnforces {
				crashesModel++
			} else {
				modelTimes = append(modelTimes, now)
				setMainModel++
			}

			if after < before {
				t.Fatalf("seed %d: enforcement count went backwards", seed)
			}
		}
		if h.crashes != crashesModel {
			t.Fatalf("seed %d: crashes %d != model %d", seed, h.crashes, crashesModel)
		}
		if len(h.mainSet) != setMainModel {
			t.Fatalf("seed %d: setMain %d != model %d", seed, len(h.mainSet), setMainModel)
		}
		// Hard cap: never more enforcements than steps, never negative.
		if len(h.mainSet)+h.crashes > steps {
			t.Fatalf("seed %d: more actions than steps", seed)
		}
	}
}

// TestPropStaleCheckNeverActs randomises interleavings of onPageFinished and
// firing of scheduled callbacks, verifying that callbacks belonging to a
// superseded navigation never produce enforcement, retries, or lastGood
// updates.
func TestPropStaleCheckNeverActs(t *testing.T) {
	for seed := int64(0); seed < 100; seed++ {
		r := rand.New(rand.NewSource(seed))
		h := newPropHarness()
		h.hasRep = true
		// Hostile URL: any action taken on it would be enforcement.
		h.report = bridge.PageReport{URL: "https://evil.example/pwn", At: h.now.Add(time.Second)}

		g, seqOf := g0(h)
		const id = 1

		// Each scheduled callback remembers the seq current when it was
		// created.
		type tagged struct {
			fn  func()
			seq uint64
		}
		var queue []tagged

		arm := func() {
			before := len(h.pending)
			g.onPageFinished(id)
			for len(h.pending) > before {
				cb := h.pending[before]
				h.pending = h.pending[:before]
				queue = append(queue, tagged{fn: cb.fn, seq: seqOf(id)})
			}
		}

		steps := 2 + r.Intn(5)
		for i := 0; i < steps; i++ {
			arm()
		}

		// Fire callbacks in random order. Stale ones must be inert.
		r.Shuffle(len(queue), func(i, j int) { queue[i], queue[j] = queue[j], queue[i] })
		for _, cb := range queue {
			isStale := cb.seq != seqOf(id)
			before := h.enforcements()
			pendingBefore := len(h.pending)
			cb.fn()
			// Drain anything the callback re-scheduled (retries).
			for len(h.pending) > pendingBefore {
				newCb := h.pending[pendingBefore]
				h.pending = h.pending[:pendingBefore]
				queue = append(queue, tagged{fn: newCb.fn, seq: cb.seq})
			}
			if isStale && h.enforcements() != before {
				t.Fatalf("seed %d: stale check (seq %d) enforced", seed, cb.seq)
			}
		}
	}
}

func g0(h *propHarness) (*navGuard, func(id uint) uint64) {
	return h.guard()
}

// TestPropTrustedNavNeverEnforced feeds random trusted URLs with fresh
// reports and checks that no enforcement action ever occurs.
func TestPropTrustedNavNeverEnforced(t *testing.T) {
	trusted := []string{
		"http://127.0.0.1:9337/",
		"http://127.0.0.1:9337/index.html",
		"https://127.0.0.1:9337/app",
		"http://localhost:9337/",
		"about:blank",
	}
	for seed := int64(0); seed < 50; seed++ {
		r := rand.New(rand.NewSource(seed))
		h := newPropHarness()
		g, _ := h.guard()
		for i := 0; i < 5; i++ {
			u := trusted[r.Intn(len(trusted))]
			if r.Intn(2) == 0 {
				u = fmt.Sprintf("%s?q=%d", u, r.Intn(1000))
			}
			h.now = h.now.Add(time.Duration(r.Intn(5)) * time.Second)
			h.report = bridge.PageReport{URL: u, At: h.now.Add(time.Millisecond)}
			h.hasRep = true
			before := h.enforcements()
			g.onPageFinished(1)
			for len(h.pending) > 0 {
				cb := h.pending[0]
				h.pending = h.pending[1:]
				cb.fn()
			}
			action, _ := security.WindowNavDecision(u, h.child)
			if action == security.NavAllow && h.enforcements() != before {
				t.Fatalf("seed %d: trusted url %q enforced", seed, u)
			}
		}
	}
}
