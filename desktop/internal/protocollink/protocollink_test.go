// SPDX-License-Identifier: 0BSD
package protocollink

import (
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

type fakePage struct {
	mu   sync.Mutex
	kind string
}

func (p *fakePage) get() string {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.kind
}

func (p *fakePage) set(k string) {
	p.mu.Lock()
	p.kind = k
	p.mu.Unlock()
}

type recorder struct {
	mu   sync.Mutex
	urls []string
}

func (r *recorder) emit(u string) {
	r.mu.Lock()
	r.urls = append(r.urls, u)
	r.mu.Unlock()
}

func (r *recorder) got() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]string(nil), r.urls...)
}

func TestOfferEmitsImmediatelyOnAppPage(t *testing.T) {
	page := &fakePage{kind: "app"}
	rec := &recorder{}
	f := New(page.get, rec.emit)

	if f.Offer("lxmf://abc") {
		t.Fatal("Offer on app page should not report queued")
	}
	if got := rec.got(); len(got) != 1 || got[0] != "lxmf://abc" {
		t.Fatalf("expected immediate emit, got %v", got)
	}
	// Nothing pending: a flush step finishes without emitting again.
	if !f.Step() {
		t.Fatal("Step on app page with empty queue should report done")
	}
	if got := rec.got(); len(got) != 1 {
		t.Fatalf("link emitted twice: %v", got)
	}
}

func TestQueuedWhileLoadingThenDeliveredOnce(t *testing.T) {
	page := &fakePage{kind: "loading"}
	rec := &recorder{}
	f := New(page.get, rec.emit)

	if !f.Offer("lxmf://cold") {
		t.Fatal("Offer while loading should report queued")
	}
	if f.Step() {
		t.Fatal("Step while loading should not be done")
	}
	if got := rec.got(); len(got) != 0 {
		t.Fatalf("emitted while loading: %v", got)
	}

	page.set("app")
	if !f.Step() {
		t.Fatal("Step on app page should report done")
	}
	if got := rec.got(); len(got) != 1 || got[0] != "lxmf://cold" {
		t.Fatalf("expected queued link delivered once, got %v", got)
	}
	// Second step must not re-emit.
	f.Step()
	if got := rec.got(); len(got) != 1 {
		t.Fatalf("link delivered twice: %v", got)
	}
}

func TestLatestQueuedLinkWins(t *testing.T) {
	page := &fakePage{kind: "loading"}
	rec := &recorder{}
	f := New(page.get, rec.emit)

	f.Offer("lxmf://first")
	f.Offer("rns://second")
	page.set("app")
	f.Step()
	if got := rec.got(); len(got) != 1 || got[0] != "rns://second" {
		t.Fatalf("expected only latest link, got %v", got)
	}
}

func TestEmptyURLIgnored(t *testing.T) {
	page := &fakePage{kind: "loading"}
	rec := &recorder{}
	f := New(page.get, rec.emit)
	if f.Offer("") {
		t.Fatal("empty url should not queue")
	}
	page.set("app")
	f.Step()
	if got := rec.got(); len(got) != 0 {
		t.Fatalf("empty url emitted: %v", got)
	}
}

func TestFlushDeliversAfterKindFlip(t *testing.T) {
	page := &fakePage{kind: "loading"}
	rec := &recorder{}
	f := New(page.get, rec.emit)
	f.Offer("lxmf://later")

	done := make(chan struct{})
	go func() {
		f.Flush(time.Millisecond, 500)
		close(done)
	}()
	time.Sleep(20 * time.Millisecond)
	page.set("app")
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("Flush did not finish after page became app")
	}
	if got := rec.got(); len(got) != 1 || got[0] != "lxmf://later" {
		t.Fatalf("expected link delivered by Flush, got %v", got)
	}
}

func TestConcurrentOfferStepNoDeadlock(t *testing.T) {
	page := &fakePage{kind: "loading"}
	rec := &recorder{}
	f := New(page.get, rec.emit)

	var stop atomic.Bool
	var wg sync.WaitGroup
	for i := 0; i < 4; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			for j := 0; j < 200 && !stop.Load(); j++ {
				f.Offer("lxmf://x")
				f.Step()
			}
		}(i)
	}
	go func() {
		for j := 0; j < 50; j++ {
			page.set("loading")
			page.set("app")
		}
		stop.Store(true)
	}()
	wg.Wait()
}
