package olc

import (
	"errors"
	"testing"
)

func TestEncodeTo_NoAllocs(t *testing.T) {
	var dst [MaxEncodedLen]byte
	allocs := testing.AllocsPerRun(1000, func() {
		n, err := EncodeTo(dst[:], -1.286386, 36.817223, 10)
		if err != nil || n == 0 {
			t.Fatal(err, n)
		}
	})
	if allocs != 0 {
		t.Fatalf("EncodeTo allocs %.3f want 0", allocs)
	}
}

func TestDecode_NoAllocs(t *testing.T) {
	const code = "6GCRPR78+CV"
	allocs := testing.AllocsPerRun(1000, func() {
		if _, err := Decode(code); err != nil {
			t.Fatal(err)
		}
	})
	if allocs != 0 {
		t.Fatalf("Decode allocs %.3f want 0", allocs)
	}
}

func TestEncodeTo_MatchesEncode(t *testing.T) {
	cases := []struct {
		lat, lng float64
		len      int
	}{
		{-1.286386, 36.817223, 10},
		{47.365590, 8.524997, 11},
		{40.689253, -74.044548, 15},
		{-89.5, 179.5, 8},
		{0, 0, 6},
	}
	var dst [MaxEncodedLen]byte
	for _, c := range cases {
		want := Encode(c.lat, c.lng, c.len)
		n, err := EncodeTo(dst[:], c.lat, c.lng, c.len)
		if err != nil {
			t.Fatal(err)
		}
		got := string(dst[:n])
		if got != want {
			t.Fatalf("EncodeTo=%q Encode=%q", got, want)
		}
		if string(EncodeBytes(c.lat, c.lng, c.len)) != want {
			t.Fatalf("EncodeBytes mismatch for %v", c)
		}
		if n != EncodedLen(c.len) {
			t.Fatalf("EncodedLen=%d n=%d", EncodedLen(c.len), n)
		}
	}
}

func TestAppendEncode_Reuse(t *testing.T) {
	buf := make([]byte, 0, 64)
	buf = AppendEncode(buf, -1.286386, 36.817223, 10)
	first := string(buf)
	want := Encode(-1.286386, 36.817223, 10)
	if first != want {
		t.Fatalf("got %q want %q", first, want)
	}
	buf = AppendEncode(buf, 47.0, 8.0, 8)
	if string(buf[:len(first)]) != want {
		t.Fatal("append overwrote prior code")
	}
}

func TestEncodeTo_ShortBuffer(t *testing.T) {
	dst := make([]byte, 4)
	_, err := EncodeTo(dst, 0, 0, 10)
	if !errors.Is(err, ErrShortBuffer) {
		t.Fatalf("got %v want ErrShortBuffer", err)
	}
}
