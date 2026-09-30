package mgrs

import "testing"
func TestFormatSpacedSingleDigitZone(t *testing.T) {
	out, err := FormatSpaced("4QFJ123456")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out != "4Q FJ 123 456" {
		t.Fatalf("got %q", out)
	}
	// Compact stays compact through the round trip.
	rt, err := FormatSpaced("4Q FJ 123 456")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rt != out {
		t.Fatalf("not idempotent: %q vs %q", rt, out)
	}
}
