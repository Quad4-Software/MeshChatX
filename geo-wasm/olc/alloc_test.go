package olc

import (
	"errors"
	"testing"
)

func TestEncodeTo_NoAllocs(t *testing.T) {
	for _, size := range []int{MaxEncodedLen, EncodedLen(10)} {
		dst := make([]byte, size)
		allocs := testing.AllocsPerRun(1000, func() {
			n, err := EncodeTo(dst, -1.286386, 36.817223, 10)
			if err != nil || n == 0 {
				t.Fatal(err, n)
			}
		})
		if allocs != 0 {
			t.Fatalf("EncodeTo size %d allocs %.3f want 0", size, allocs)
		}
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
		exact := make([]byte, EncodedLen(c.len))
		exactN, err := EncodeTo(exact, c.lat, c.lng, c.len)
		if err != nil {
			t.Fatalf("EncodeTo exact buffer: %v", err)
		}
		if exactN != len(exact) || string(exact) != want {
			t.Fatalf("EncodeTo exact buffer=%q len %d want %q len %d", exact, exactN, want, len(want))
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
	dst := make([]byte, EncodedLen(10)-1)
	_, err := EncodeTo(dst, 0, 0, 10)
	if !errors.Is(err, ErrShortBuffer) {
		t.Fatalf("got %v want ErrShortBuffer", err)
	}
}

func TestAppendShorten_NoAllocs(t *testing.T) {
	buf := make([]byte, 0, MaxEncodedLen)
	allocs := testing.AllocsPerRun(1000, func() {
		var err error
		if buf, err = AppendShorten(buf[:0], "9C3W9QCJ+2VX", 51.3708675, -1.217765625); err != nil {
			t.Fatal(err)
		}
	})
	if allocs != 0 {
		t.Fatalf("AppendShorten allocs %.3f want 0", allocs)
	}
}

func TestAppendRecoverNearest_NoAllocs(t *testing.T) {
	buf := make([]byte, 0, MaxEncodedLen)
	allocs := testing.AllocsPerRun(1000, func() {
		var err error
		if buf, err = AppendRecoverNearest(buf[:0], "45+G6", 14.95125, -23.5001); err != nil {
			t.Fatal(err)
		}
	})
	if allocs != 0 {
		t.Fatalf("AppendRecoverNearest allocs %.3f want 0", allocs)
	}
}

func TestAppendEncode_Growth(t *testing.T) {
	for _, initialLen := range []int{0, 1, 3, 20} {
		buf := make([]byte, initialLen)
		for i := range buf {
			buf[i] = 'x'
		}
		prefix := string(buf)
		got := AppendEncode(buf, 0, 0, 10)
		want := prefix + Encode(0, 0, 10)
		if string(got) != want {
			t.Errorf("len %d: got %q want %q", initialLen, got, want)
		}
	}
}

func TestEncodedLen_Clipping(t *testing.T) {
	cases := []struct {
		codeLen int
		want    int
	}{
		{-1, 11},
		{0, 11},
		{1, 9},
		{2, 9},
		{7, 9},
		{8, 9},
		{9, 11},
		{10, 11},
		{15, 16},
		{100, 16},
	}
	for _, tc := range cases {
		if got := EncodedLen(tc.codeLen); got != tc.want {
			t.Errorf("EncodedLen(%d)=%d want %d", tc.codeLen, got, tc.want)
		}
	}
}
