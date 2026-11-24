package main

import (
	"testing"
	"time"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/bridge"
)

type navFake struct {
	now       time.Time
	report    bridge.PageReport
	hasRep    bool
	child     bool
	closed    []uint
	mainSet   []string
	extOpened []string
	crashed   int
	scheduled []func()
}

func newNavFake() *navFake { return &navFake{now: time.Now()} }

func (f *navFake) guard() *navGuard {
	g := newNavGuard("http://127.0.0.1:9337/__shell/loading.html")
	g.now = func() time.Time { return f.now }
	g.schedule = func(d time.Duration, fn func()) func() {
		f.scheduled = append(f.scheduled, fn)
		return func() {}
	}
	g.report = func(id uint) (bridge.PageReport, bool) { return f.report, f.hasRep }
	g.isChild = func(id uint) bool { return f.child }
	g.closeByID = func(id uint) { f.closed = append(f.closed, id) }
	g.setMain = func(u string) { f.mainSet = append(f.mainSet, u) }
	g.openExt = func(u string) { f.extOpened = append(f.extOpened, u) }
	g.crash = func() { f.crashed++ }
	g.log = func(string) {}
	return g
}

func (f *navFake) fireLast() {
	fn := f.scheduled[len(f.scheduled)-1]
	f.scheduled = f.scheduled[:len(f.scheduled)-1]
	fn()
}

func TestNavGuardAllowsTrustedURL(t *testing.T) {
	f := newNavFake()
	g := f.guard()
	f.hasRep = true
	f.report = bridge.PageReport{URL: "http://127.0.0.1:9337/", At: f.now.Add(time.Second)}
	g.onPageFinished(1)
	f.fireLast() // first check: report already fresh
	if len(f.mainSet) != 0 || len(f.closed) != 0 || f.crashed != 0 {
		t.Fatalf("trusted URL enforced: %+v", f)
	}
	g.mu.Lock()
	lg := g.lastGood
	g.mu.Unlock()
	if lg != "http://127.0.0.1:9337/" {
		t.Fatalf("lastGood = %q", lg)
	}
}

func TestNavGuardRestoresOnSilentForeignPage(t *testing.T) {
	f := newNavFake()
	g := f.guard()
	f.hasRep = false // foreign page: no bridge, no report
	g.onPageFinished(1)
	f.fireLast() // first check: no report -> retry armed
	if len(f.mainSet) != 0 {
		t.Fatal("enforced before retry")
	}
	f.fireLast() // retry: still nothing -> enforce
	if len(f.mainSet) != 1 || f.mainSet[0] != "http://127.0.0.1:9337/__shell/loading.html" {
		t.Fatalf("restore = %v", f.mainSet)
	}
}

func TestNavGuardStaleReportDoesNotCount(t *testing.T) {
	f := newNavFake()
	g := f.guard()
	// Report exists but predates this page-finish (previous page's URL).
	f.hasRep = true
	f.report = bridge.PageReport{URL: "http://127.0.0.1:9337/old", At: f.now.Add(-time.Minute)}
	g.onPageFinished(1)
	f.fireLast()
	f.fireLast() // retry -> stale report still not fresh -> enforce
	if len(f.mainSet) != 1 {
		t.Fatalf("stale report allowed navigation: %v", f.mainSet)
	}
}

func TestNavGuardExternalURLOpensBrowser(t *testing.T) {
	f := newNavFake()
	g := f.guard()
	f.hasRep = true
	f.report = bridge.PageReport{URL: "https://example.com/x", At: f.now.Add(time.Second)}
	g.onPageFinished(1)
	f.fireLast()
	if len(f.extOpened) != 1 || f.extOpened[0] != "https://example.com/x" {
		t.Fatalf("openExternal = %v", f.extOpened)
	}
	if len(f.mainSet) != 1 {
		t.Fatalf("restore missing: %v", f.mainSet)
	}
}

func TestNavGuardClosesChildWindow(t *testing.T) {
	f := newNavFake()
	f.child = true
	g := f.guard()
	f.hasRep = true
	f.report = bridge.PageReport{URL: "https://evil.example/", At: f.now.Add(time.Second)}
	g.onPageFinished(7)
	f.fireLast()
	if len(f.closed) != 1 || f.closed[0] != 7 {
		t.Fatalf("closed = %v", f.closed)
	}
	if len(f.mainSet) != 0 {
		t.Fatal("child window got main-window restore")
	}
}

func TestNavGuardRateLimitEscalates(t *testing.T) {
	f := newNavFake()
	g := f.guard()
	f.hasRep = true
	f.report = bridge.PageReport{URL: "https://evil.example/", At: f.now.Add(time.Second)}
	for i := 0; i < navMaxEnforces; i++ {
		g.onPageFinished(1)
		f.fireLast()
		if f.crashed != 0 {
			t.Fatalf("crashed at enforcement %d", i+1)
		}
	}
	g.onPageFinished(1)
	f.fireLast()
	if f.crashed != 1 {
		t.Fatalf("crashed = %d, want 1", f.crashed)
	}
}

func TestNavGuardDataURLNoExternal(t *testing.T) {
	f := newNavFake()
	g := f.guard()
	f.hasRep = true
	f.report = bridge.PageReport{URL: "data:text/html,<script>x</script>", At: f.now.Add(time.Second)}
	g.onPageFinished(1)
	f.fireLast()
	if len(f.extOpened) != 0 {
		t.Fatalf("data: URL opened externally: %v", f.extOpened)
	}
	if len(f.mainSet) != 1 {
		t.Fatal("data: URL not restored")
	}
}
