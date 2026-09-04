package mgrs

import (
	"math"
	"testing"
)

func TestSmokeExportedAPIWarmPath(t *testing.T) {
	lat := 52.658
	lon := 5.892
	z, err := LongitudeZone(lat, lon)
	if err != nil {
		t.Fatal(err)
	}
	if z < 1 || z > 60 {
		t.Fatalf("LongitudeZone unreasonable %d", z)
	}
	s, err := Encode(lat, lon, DefaultDigitPairs)
	if err != nil || len(s) < 13 {
		t.Fatalf("Encode %q err=%v", s, err)
	}

	sw, err := Decode(s, false)
	if err != nil {
		t.Fatal(err)
	}
	center, err := Decode(s, true)
	if err != nil {
		t.Fatal(err)
	}
	dLatM := (center.Lat - sw.Lat) * 111_319.5
	dLonM := (center.Lon - sw.Lon) * 111_319.5 * math.Cos(sw.Lat*degRad)
	d := math.Hypot(dLatM, dLonM)
	const wantShiftMeters = 0.05
	if d <= wantShiftMeters {
		t.Fatalf("decode center/sw expected >%.1fm positional delta for %s, got %.4fm", wantShiftMeters, s, d)
	}
}

func TestSmokeSouthernRoundTrip(t *testing.T) {
	lat := -37.814
	lon := 144.963
	s, err := Encode(lat, lon, DefaultDigitPairs)
	if err != nil {
		t.Fatal(err)
	}
	pt, err := Decode(s, false)
	if err != nil {
		t.Fatal(err)
	}
	clat := math.Max(math.Abs(math.Cos(lat*degRad)), 1e-3)
	maxLat := 2e-3
	maxLon := maxLat / clat

	if math.Abs(pt.Lat-lat) > maxLat || math.Abs(pt.Lon-lon) > maxLon {
		t.Fatalf("decoded drift %+v versus input lat=%v lon=%v via %s", pt, lat, lon, s)
	}
}
