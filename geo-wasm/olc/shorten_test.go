package olc

import "testing"
func TestRecoverNearestLongTail(t *testing.T) {
	// Long-but-valid short codes must not overflow the merged buffer.
	c, err := RecoverNearest("2345+CFGHJMPQRVWX", 51.0, 0.1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c == "" {
		t.Fatal("empty code")
	}
}

func TestShortenShortUnpaddedCode(t *testing.T) {
	// 6-7 char unpadded codes must not panic or emit a bare separator.
	// 8-digit full codes (no grid part) must never emit a bare "+".
	c, err := Shorten("849CR2F8+", 47.6497, 8.3493)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c == "+" || c == "" {
		t.Fatalf("degenerate code %q", c)
	}
}
