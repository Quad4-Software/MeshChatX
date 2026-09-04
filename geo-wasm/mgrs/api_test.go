package mgrs

import (
	"errors"
	"math"
	"testing"
)

func TestCheckCoords_UpperBoundaryNudge(t *testing.T) {
	north := true
	x := 900_000.0
	y := 5_000_000.0
	if err := checkCoords(true, &north, &x, &y); err != nil {
		t.Fatal(err)
	}
	if x >= 900_000 {
		t.Fatalf("expected easting nudge below 900km, got %v", x)
	}

	north = false
	x = 500_000
	y = 10_000_000.0
	if err := checkCoords(true, &north, &x, &y); err != nil {
		t.Fatal(err)
	}
	if y >= 10_000_000 {
		t.Fatalf("expected northing nudge below 10000km, got %v", y)
	}
}

func TestCheckCoords_OutOfRange(t *testing.T) {
	north := true
	x := 50_000.0
	y := 5_000_000.0
	if err := checkCoords(true, &north, &x, &y); !errors.Is(err, ErrInvalidGrid) {
		t.Fatalf("got %v want ErrInvalidGrid", err)
	}
}

func TestEncodeGrid_BaghdadSquare(t *testing.T) {
	g := Grid{Zone: 38, North: true, Easting: 444_000, Northing: 3_688_000}
	s, err := EncodeGrid(g, 2)
	if err != nil {
		t.Fatal(err)
	}
	if s != "38SMB4488" {
		t.Fatalf("got %q want 38SMB4488", s)
	}
}

func TestLatLonToGrid_PolarDispatch(t *testing.T) {
	g, err := LatLonToGrid(85, 10)
	if err != nil {
		t.Fatal(err)
	}
	if g.Zone != ZoneUPS || !g.North {
		t.Fatalf("got %+v", g)
	}
	g, err = LatLonToGrid(-82, -40)
	if err != nil {
		t.Fatal(err)
	}
	if g.Zone != ZoneUPS || g.North {
		t.Fatalf("got %+v", g)
	}
	g, err = LatLonToGrid(52.658, 5.892)
	if err != nil {
		t.Fatal(err)
	}
	if g.Zone != 31 {
		t.Fatalf("zone got %d want 31", g.Zone)
	}
}

func TestUPS_RoundTripPolarSamples(t *testing.T) {
	samples := []struct {
		lat, lon float64
	}{
		{-89.99999, 45},
		{-85, 77.85},
		{-82, -60},
		{85, 0},
		{88, 45},
		{84.1, -120},
	}
	for _, s := range samples {
		ref, err := Encode(s.lat, s.lon, DefaultDigitPairs)
		if err != nil {
			t.Fatalf("Encode(%v,%v): %v", s.lat, s.lon, err)
		}
		pt, err := Decode(ref, true)
		if err != nil {
			t.Fatalf("Decode(%s): %v", ref, err)
		}
		dLatM := (pt.Lat - s.lat) * 111_111
		cosClamp := math.Max(math.Abs(math.Cos(s.lat*degRad)), 1e-3)
		dLonM := (pt.Lon - s.lon) * 111_111 * cosClamp
		if math.Hypot(dLatM, dLonM) > 5 {
			t.Fatalf("%s round-trip too wide: dLat_m=%.3f dLon_m=%.3f from (%v,%v) -> (%v,%v)",
				ref, dLatM, dLonM, s.lat, s.lon, pt.Lat, pt.Lon)
		}
	}
}

func TestUPS_KnownCatalogStrings(t *testing.T) {
	cases := []struct {
		lat, lon float64
		want     string
	}{
		{-89.99999, 45, "BAN0000000000"},
		{-85, 77.85, "BHP4301516908"},
		{-82, -60, "AQS2960244788"},
	}
	for _, tc := range cases {
		got, err := Encode(tc.lat, tc.lon, 5)
		if err != nil {
			t.Fatal(err)
		}
		if got != tc.want {
			t.Fatalf("Encode(%v,%v)=%q want %q", tc.lat, tc.lon, got, tc.want)
		}
	}
}

func TestDecodeParts_UTMAndUPS(t *testing.T) {
	p, err := DecodeParts("38SMB4488", false)
	if err != nil {
		t.Fatal(err)
	}
	if p.Zone != 38 || !p.North || p.Band != 'S' || p.Col != 'M' || p.Row != 'B' || p.DigitPairs != 2 {
		t.Fatalf("utm parts %+v", p)
	}
	if math.Abs(p.Easting-444000) > 1 || math.Abs(p.Northing-3688000) > 1 {
		t.Fatalf("utm metres E=%v N=%v", p.Easting, p.Northing)
	}

	ref, err := Encode(-89.99999, 45, 5)
	if err != nil {
		t.Fatal(err)
	}
	p, err = DecodeParts(ref, false)
	if err != nil {
		t.Fatal(err)
	}
	if p.Zone != ZoneUPS || p.North || p.DigitPairs != 5 {
		t.Fatalf("ups parts %+v compact=%s", p, ref)
	}
}

func TestFormatSpaced(t *testing.T) {
	pretty, err := FormatSpaced("38SMB4488")
	if err != nil {
		t.Fatal(err)
	}
	if pretty != "38S MB 44 88" {
		t.Fatalf("got %q", pretty)
	}
	a, err := Decode("38SMB4488", false)
	if err != nil {
		t.Fatal(err)
	}
	b, err := Decode(pretty, false)
	if err != nil {
		t.Fatal(err)
	}
	if a != b {
		t.Fatalf("spaced decode diverge %+v vs %+v", a, b)
	}

	compact, err := Encode(52.658, 5.892, DefaultDigitPairs)
	if err != nil {
		t.Fatal(err)
	}
	pretty, err = FormatSpaced(compact)
	if err != nil {
		t.Fatal(err)
	}
	again, err := FormatSpaced(pretty)
	if err != nil {
		t.Fatal(err)
	}
	if again != pretty {
		t.Fatalf("FormatSpaced not idempotent %q vs %q", pretty, again)
	}
}
