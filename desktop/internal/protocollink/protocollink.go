// SPDX-License-Identifier: 0BSD
// Package protocollink forwards deep links (lxmf://, rns://) to the app page.
// A link offered while the page is still on the loading screen is queued and
// flushed once the page kind becomes "app"; links offered on the app page are
// emitted immediately. Only the most recent queued link is kept.
package protocollink

import (
	"sync"
	"time"
)

// Forwarder queues at most one pending deep link and emits it when the page
// is ready. kind reports the current page kind ("" until known, "app" when
// the real app page is showing); emit delivers a URL to the page.
type Forwarder struct {
	mu      sync.Mutex
	pending string
	kind    func() string
	emit    func(url string)
}

// New returns a Forwarder. kind and emit may be called from any goroutine;
// they must not call back into the Forwarder.
func New(kind func() string, emit func(url string)) *Forwarder {
	return &Forwarder{kind: kind, emit: emit}
}

// Offer handles an incoming link. It reports whether the link was queued
// (i.e. the caller should start a Flush loop); when the page is already "app"
// the link is emitted immediately and Offer returns false.
func (f *Forwarder) Offer(url string) bool {
	if url == "" {
		return false
	}
	if f.kind() == "app" {
		f.emit(url)
		return false
	}
	f.mu.Lock()
	f.pending = url
	f.mu.Unlock()
	return true
}

// Step performs a single flush check and reports whether flushing is done
// (page is "app" — with or without a pending link). When a pending link exists
// on the app page it is cleared and emitted exactly once.
func (f *Forwarder) Step() bool {
	if f.kind() != "app" {
		return false
	}
	f.mu.Lock()
	pending := f.pending
	f.pending = ""
	f.mu.Unlock()
	if pending == "" {
		return true
	}
	f.emit(pending)
	return true
}

// Flush blocks until the pending link is delivered or the page reaches "app"
// with nothing pending, retrying every interval for maxAttempts checks.
// A zero interval defaults to 500ms; zero maxAttempts defaults to 240.
func (f *Forwarder) Flush(interval time.Duration, maxAttempts int) {
	if interval <= 0 {
		interval = 500 * time.Millisecond
	}
	if maxAttempts <= 0 {
		maxAttempts = 240
	}
	for i := 0; i < maxAttempts; i++ {
		if f.Step() {
			return
		}
		time.Sleep(interval)
	}
}
