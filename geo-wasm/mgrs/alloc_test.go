package mgrs

import (
	"bytes"
	"errors"
	"testing"
)

func TestAppendEncode_NoAllocsWithSufficientCapacity(t *testing.T) {
	const runs = 1000
	dst := make([]byte, 0, 32)
	allocs := testing.AllocsPerRun(runs, func() {
		buf := dst[:0]
		out, err := AppendEncode(buf, 52.658, 5.892, DefaultDigitPairs)
		if err != nil {
			panic(err)
		}
		if len(out) == 0 {
			panic("empty output")
		}
	})
	if allocs != 0 {
		t.Fatalf("expected zero allocations, got %.3f", allocs)
	}
}

func TestEncodeTo_NoAllocsWithSufficientCapacity(t *testing.T) {
	const runs = 1000
	var dst [MaxEncodedLen]byte
	allocs := testing.AllocsPerRun(runs, func() {
		n, err := EncodeTo(dst[:], 52.658, 5.892, DefaultDigitPairs)
		if err != nil {
			panic(err)
		}
		if n <= 0 {
			panic("nothing written")
		}
	})
	if allocs != 0 {
		t.Fatalf("expected zero allocations, got %.3f", allocs)
	}
}

func TestEncodeTo_ShortBuffer(t *testing.T) {
	dst := make([]byte, 2)
	_, err := EncodeTo(dst, 52.658, 5.892, DefaultDigitPairs)
	if !errors.Is(err, ErrShortBuffer) {
		t.Fatalf("got %v want %v", err, ErrShortBuffer)
	}
}

func TestEncodeTo_EqualsEncodeBytes(t *testing.T) {
	want, err := EncodeBytes(52.658, 5.892, DefaultDigitPairs)
	if err != nil {
		t.Fatal(err)
	}
	var dst [MaxEncodedLen]byte
	n, err := EncodeTo(dst[:], 52.658, 5.892, DefaultDigitPairs)
	if err != nil {
		t.Fatal(err)
	}
	got := dst[:n]
	if !bytes.Equal(got, want) {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestEncodeGridTo_NoAllocsUTMAndUPS(t *testing.T) {
	const runs = 1000
	var dst [MaxEncodedLen]byte
	gUTM := Grid{Zone: 31, North: true, Easting: 595591.0, Northing: 5838152.0}
	allocs := testing.AllocsPerRun(runs, func() {
		n, err := EncodeGridTo(dst[:], gUTM, DefaultDigitPairs)
		if err != nil {
			panic(err)
		}
		if n <= 0 {
			panic("empty")
		}
	})
	if allocs != 0 {
		t.Fatalf("utm EncodeGridTo allocs %.3f", allocs)
	}

	gUPS, err := LatLonToGrid(85, 10)
	if err != nil {
		t.Fatal(err)
	}
	allocs = testing.AllocsPerRun(runs, func() {
		n, err := EncodeGridTo(dst[:], gUPS, DefaultDigitPairs)
		if err != nil {
			panic(err)
		}
		if n <= 0 {
			panic("empty")
		}
	})
	if allocs != 0 {
		t.Fatalf("ups EncodeGridTo allocs %.3f", allocs)
	}

	allocs = testing.AllocsPerRun(runs, func() {
		n, err := EncodeTo(dst[:], 85, 10, DefaultDigitPairs)
		if err != nil {
			panic(err)
		}
		if n <= 0 {
			panic("empty")
		}
	})
	if allocs != 0 {
		t.Fatalf("polar EncodeTo allocs %.3f", allocs)
	}
}
