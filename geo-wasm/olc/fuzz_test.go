package olc

import (
	"math"
	"testing"
)

func FuzzEncodeDecodeRoundTrip(f *testing.F) {
	seeds := []struct {
		lat, lng float64
		length   int
	}{
		{-1.286386, 36.817223, 10},
		{47.365590, 8.524997, 11},
		{0, 0, 8},
		{-89.9, 179.9, 15},
		{90, -180, 10},
	}
	for _, s := range seeds {
		f.Add(s.lat, s.lng, s.length)
	}
	f.Fuzz(func(t *testing.T, lat, lng float64, length int) {
		if math.IsNaN(lat) || math.IsNaN(lng) || math.IsInf(lat, 0) || math.IsInf(lng, 0) {
			t.Skip()
		}
		if lat < -90 || lat > 90 {
			t.Skip()
		}
		code := Encode(lat, lng, length)
		if !IsFull(code) {
			t.Skip()
		}
		area, err := Decode(code)
		if err != nil {
			t.Fatalf("Decode(%q): %v", code, err)
		}
		clat, clng := area.Center()
		again := Encode(clat, clng, area.Len)
		if StripCode(again) != StripCode(code) {
			t.Fatalf("center re-encode %q != %q for input (%v,%v)", again, code, lat, lng)
		}
	})
}
