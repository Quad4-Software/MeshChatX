package olc

import "testing"

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

func FuzzCodeOperations(f *testing.F) {
	seeds := []string{
		"6GCRPR78+CV",
		"8FWCX400+",
		"45+G6",
		"+G6GGGGGGGGGGGGGGGG",
		"849VGJQF+VX7QR3JW",
		"8FWC2_45+G6",
		"8FWC2η45+G6",
		"\xff\xfe+",
	}
	for _, code := range seeds {
		f.Add(code, 37.5397, -122.3751)
	}
	f.Fuzz(func(t *testing.T, code string, lat, lng float64) {
		if CheckFull(code) == nil {
			if _, err := Decode(code); err != nil {
				t.Fatalf("Decode(%q): %v", code, err)
			}
			_, _ = Shorten(code, lat, lng)
		}
		if CheckShort(code) == nil {
			if _, err := RecoverNearest(code, lat, lng); err != nil {
				t.Fatalf("RecoverNearest(%q): %v", code, err)
			}
		}
	})
}
