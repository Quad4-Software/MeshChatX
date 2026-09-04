package mgrs

import (
	"runtime"
	"testing"
)

func TestLeakEncodeDecodeBurstSteady(t *testing.T) {
	lat := 52.658
	lon := 5.892
	runtime.GC()
	before := runtime.NumGoroutine()
	const n = 2000
	for range n {
		s, err := Encode(lat, lon, DefaultDigitPairs)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := Decode(s, false); err != nil {
			t.Fatal(err)
		}
	}
	runtime.GC()
	after := runtime.NumGoroutine()
	const slack = 8
	if after-before > slack {
		t.Fatalf("goroutine drift before=%d after=%d slack=%d", before, after, slack)
	}
}
