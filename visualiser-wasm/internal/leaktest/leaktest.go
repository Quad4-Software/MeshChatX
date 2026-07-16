// SPDX-License-Identifier: 0BSD

// Package leaktest provides lightweight goroutine leak checks without deps.
package leaktest

import (
	"runtime"
	"testing"
	"time"
)

// Check returns a cleanup that fails the test if goroutines leaked.
func Check(t testing.TB) func() {
	t.Helper()
	runtime.GC()
	time.Sleep(5 * time.Millisecond)
	before := runtime.NumGoroutine()
	return func() {
		t.Helper()
		deadline := time.Now().Add(500 * time.Millisecond)
		var after int
		for {
			runtime.GC()
			after = runtime.NumGoroutine()
			if after <= before {
				return
			}
			if time.Now().After(deadline) {
				t.Fatalf("goroutine leak: before=%d after=%d", before, after)
			}
			time.Sleep(10 * time.Millisecond)
		}
	}
}
