package mgrs

import (
	"errors"
	"testing"
)

func TestUnitEncode_digitPairsBoundary(t *testing.T) {
	s, err := Encode(10, 20, GridZoneOnly)
	if err != nil {
		t.Fatalf("Encode grid-zone-only: %v", err)
	}
	if len(s) != 3 {
		t.Fatalf("Encode grid-zone-only = %q, want 3 characters", s)
	}
	_, err = Encode(10, 20, GridZoneOnly-1)
	if !errors.Is(err, ErrInvalidDigitPairs) {
		t.Fatalf("got %v want ErrInvalidDigitPairs", err)
	}
	_, err = Encode(10, 20, MaxDigitPairs+3)
	if !errors.Is(err, ErrInvalidDigitPairs) {
		t.Fatalf("got %v want ErrInvalidDigitPairs", err)
	}
}

func TestUnitEncode_latitudeBelt(t *testing.T) {
	_, err := LongitudeZone(-82, 40)
	if !errors.Is(err, ErrLatOutOfUTMRange) {
		t.Fatalf("LongitudeZone south polar: got %v", err)
	}
	_, err = LongitudeZone(85, 0)
	if !errors.Is(err, ErrLatOutOfUTMRange) {
		t.Fatalf("LongitudeZone north polar: got %v", err)
	}
	s, err := Encode(-82, 40, DefaultDigitPairs)
	if err != nil {
		t.Fatalf("Encode south UPS: %v", err)
	}
	if s[0] != 'A' && s[0] != 'B' {
		t.Fatalf("south UPS GZD want A/B got %q", s)
	}
	s, err = Encode(85, 0, DefaultDigitPairs)
	if err != nil {
		t.Fatalf("Encode north UPS: %v", err)
	}
	if s[0] != 'Y' && s[0] != 'Z' {
		t.Fatalf("north UPS GZD want Y/Z got %q", s)
	}
}

func TestUnitDecode_whitespaceInvariant(t *testing.T) {
	s, err := Encode(-33.8136, 144.9631, DefaultDigitPairs)
	if err != nil {
		t.Fatal(err)
	}
	ref, err := Decode(s, false)
	if err != nil {
		t.Fatal(err)
	}
	spaced, err := Decode("  \t"+s+"\n  ", false)
	if err != nil {
		t.Fatal(err)
	}
	if spaced != ref {
		t.Fatalf("whitespace divergence %+v vs %+v", ref, spaced)
	}
}

func TestUnitDecode_oddDigitTail(t *testing.T) {
	_, err := Decode("03UXD982817461", false)
	if err == nil {
		t.Fatal("expected error for odd digit count")
	}
}

func TestUnitDecode_zeroZoneRejected(t *testing.T) {
	_, err := Decode("00UXD98281746211", false)
	if !errors.Is(err, ErrInvalidMGRS) {
		t.Fatalf("got %v want ErrInvalidMGRS", err)
	}
}

func TestUnitDecode_zoneLeadingZeroAccepted(t *testing.T) {
	withZero, err := DecodeParts("01CDM4186716915", false)
	if err != nil {
		t.Fatalf("DecodeParts padded zone: %v", err)
	}
	withoutZero, err := DecodeParts("1CDM4186716915", false)
	if err != nil {
		t.Fatalf("DecodeParts unpadded zone: %v", err)
	}
	if withZero.Zone != 1 || withoutZero.Zone != 1 {
		t.Fatalf("zones = %d, %d, want 1", withZero.Zone, withoutZero.Zone)
	}
	if withZero.Point != withoutZero.Point || withZero.Easting != withoutZero.Easting || withZero.Northing != withoutZero.Northing {
		t.Fatalf("padded and unpadded zones differ: %+v vs %+v", withZero, withoutZero)
	}
}

func TestUnitEncode_gridZoneOnly(t *testing.T) {
	cases := []struct {
		lat  float64
		lon  float64
		want string
	}{
		{52.658, 5.892, "31U"},
		{-85, -77.85, "A"},
		{-85, 77.85, "B"},
		{85, -77.85, "Y"},
		{85, 77.85, "Z"},
	}
	for _, tc := range cases {
		got, err := Encode(tc.lat, tc.lon, GridZoneOnly)
		if err != nil {
			t.Fatalf("Encode(%v, %v): %v", tc.lat, tc.lon, err)
		}
		if got != tc.want {
			t.Fatalf("Encode(%v, %v) = %q, want %q", tc.lat, tc.lon, got, tc.want)
		}
		p, err := DecodeParts(got, false)
		if err != nil {
			t.Fatalf("DecodeParts(%q): %v", got, err)
		}
		if p.DigitPairs != GridZoneOnly {
			t.Fatalf("DecodeParts(%q) precision = %d, want %d", got, p.DigitPairs, GridZoneOnly)
		}
	}
}
