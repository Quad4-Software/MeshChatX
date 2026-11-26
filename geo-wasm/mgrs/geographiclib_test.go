package mgrs

import (
	"math"
	"testing"
)

func almostEqual(got, want, tol float64) bool {
	return math.Abs(got-want) <= tol
}

func TestGeographicLibReferenceVectors(t *testing.T) {
	cases := []struct {
		name string
		lat  float64
		lon  float64
		mgrs string
	}{
		{"norway west edge", 56, 2.999999999999, "31VDC9999906079"},
		{"norway widened zone west edge", 56, 3, "32VJH2604922336"},
		{"norway widened zone east edge", 56, 8.999999999999, "32VMH9999906079"},
		{"svalbard 31 west edge", 72, 5.999999999999, "31XFV0343391508"},
		{"svalbard 31 east edge", 72, 6, "31XFV0343391508"},
		{"svalbard 32 absent", 72, 11.999999999999, "33XUV9656691508"},
		{"svalbard 33 west edge", 72, 12, "33XUV9656691508"},
		{"svalbard 33 east edge", 72, 17.999999999999, "33XXV0343391508"},
		{"svalbard 34 absent", 72, 18, "33XXV0343391508"},
		{"svalbard 35 west edge", 72, 23.999999999999, "35XLV9656691508"},
		{"svalbard 35 east edge", 72, 24, "35XLV9656691508"},
		{"svalbard 36 absent", 72, 35.999999999999, "37XCV9656691508"},
		{"svalbard 37 west edge", 72, 36, "37XCV9656691508"},
		{"utm north boundary west", 83.999999999999, -179.999999999999, "01XDP6500529005"},
		{"ups north boundary west", 84, -180, "ZAP0000066727"},
		{"ups north boundary east", 84, 179.999999999999, "ZAP0000066727"},
		{"utm south boundary west", -79.999999999999, -180, "01CDM4186716915"},
		{"ups south boundary east", -80, 179.999999999999, "60CWS5813216915"},
		{"south pole approach", -89.999999999999, 0, "BAN0000000000"},
		{"north pole approach", 89.999999999999, 0, "ZAG0000099999"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := Encode(tc.lat, tc.lon, DefaultDigitPairs)
			if err != nil {
				t.Fatalf("Encode error: %v", err)
			}
			if got != tc.mgrs {
				t.Fatalf("Encode = %q, want %q", got, tc.mgrs)
			}

			p, err := DecodeParts(tc.mgrs, false)
			if err != nil {
				t.Fatalf("DecodeParts error: %v", err)
			}
			if p.Compact != tc.mgrs {
				t.Fatalf("Compact = %q, want %q", p.Compact, tc.mgrs)
			}
		})
	}
}

func TestGridZoneOnlyReferences(t *testing.T) {
	cases := []struct {
		ref      string
		zone     int
		north    bool
		band     byte
		easting  float64
		northing float64
		lat      float64
		lon      float64
	}{
		{"31U", 31, true, 'U', 500000, 5800000, 52.35029334885088, 3},
		{"31V", 31, true, 'V', 400000, 6700000, 60.42389879597798, 1.18372878571729},
		{"A", ZoneUPS, false, 'A', 1600000, 2000000, -86.39830793812162, -90},
		{"B", ZoneUPS, false, 'B', 2400000, 2000000, -86.39830793812162, 90},
		{"Y", ZoneUPS, true, 'Y', 1600000, 2000000, 86.39830793812162, -90},
		{"Z", ZoneUPS, true, 'Z', 2400000, 2000000, 86.39830793812162, 90},
	}
	for _, tc := range cases {
		t.Run(tc.ref, func(t *testing.T) {
			p, err := DecodeParts(tc.ref, true)
			if err != nil {
				t.Fatalf("DecodeParts error: %v", err)
			}
			if p.Compact != tc.ref || p.Zone != tc.zone || p.North != tc.north || p.Band != tc.band || p.DigitPairs != -1 {
				t.Fatalf("decoded identity = %+v", p)
			}
			if p.Easting != tc.easting || p.Northing != tc.northing {
				t.Fatalf("grid = %.12f %.12f, want %.12f %.12f", p.Easting, p.Northing, tc.easting, tc.northing)
			}
			if !almostEqual(p.Point.Lat, tc.lat, 1e-10) || !almostEqual(p.Point.Lon, tc.lon, 1e-10) {
				t.Fatalf("point = %.11f %.11f, want %.11f %.11f", p.Point.Lat, p.Point.Lon, tc.lat, tc.lon)
			}
			pretty, err := FormatSpaced(tc.ref)
			if err != nil {
				t.Fatalf("FormatSpaced error: %v", err)
			}
			if pretty != tc.ref {
				t.Fatalf("FormatSpaced = %q, want %q", pretty, tc.ref)
			}
		})
	}
}

func TestLongitudeWrapsToCanonicalRange(t *testing.T) {
	base, err := Encode(0, -180, DefaultDigitPairs)
	if err != nil {
		t.Fatalf("Encode baseline error: %v", err)
	}
	for _, lon := range []float64{180, 540, -540, 900, -180 + 360*1e9} {
		got, err := Encode(0, lon, DefaultDigitPairs)
		if err != nil {
			t.Fatalf("Encode(%v) error: %v", lon, err)
		}
		if got != base {
			t.Fatalf("Encode(%v) = %q, want %q", lon, got, base)
		}
	}

	z190, err := LongitudeZone(0, 190)
	if err != nil {
		t.Fatalf("LongitudeZone(190) error: %v", err)
	}
	zMinus170, err := LongitudeZone(0, -170)
	if err != nil {
		t.Fatalf("LongitudeZone(-170) error: %v", err)
	}
	if z190 != zMinus170 {
		t.Fatalf("LongitudeZone(190) = %d, want %d", z190, zMinus170)
	}
}

func TestNonFiniteInputsRejected(t *testing.T) {
	bad := []float64{math.NaN(), math.Inf(1), math.Inf(-1)}
	for _, v := range bad {
		if _, err := LatLonToGrid(v, 0); err == nil {
			t.Fatalf("LatLonToGrid(%v, 0) succeeded", v)
		}
		if _, err := LatLonToGrid(0, v); err == nil {
			t.Fatalf("LatLonToGrid(0, %v) succeeded", v)
		}
		if _, err := LongitudeZone(0, v); err == nil {
			t.Fatalf("LongitudeZone(0, %v) succeeded", v)
		}
		if _, err := Encode(0, v, DefaultDigitPairs); err == nil {
			t.Fatalf("Encode(0, %v) succeeded", v)
		}
		if _, err := GridToLatLon(Grid{Zone: 31, North: true, Easting: v, Northing: 5000000}); err == nil {
			t.Fatalf("GridToLatLon easting %v succeeded", v)
		}
		if _, err := EncodeGrid(Grid{Zone: 31, North: true, Easting: 500000, Northing: v}, DefaultDigitPairs); err == nil {
			t.Fatalf("EncodeGrid northing %v succeeded", v)
		}
	}
}

func TestProjectionInverseRoundTripInMetres(t *testing.T) {
	utmCases := []struct {
		lat float64
		lon float64
	}{
		{0, 0},
		{52.658, 5.892},
		{-33.8688, 151.2093},
		{83.999999, -179.999999},
		{-79.999999, 179.999999},
		{72, 6},
		{56, 3},
	}
	for _, tc := range utmCases {
		zone, err := LongitudeZone(tc.lat, tc.lon)
		if err != nil {
			t.Fatalf("LongitudeZone(%v, %v): %v", tc.lat, tc.lon, err)
		}
		south := tc.lat < 0
		e, n := forwardTM(tc.lat, tc.lon, zone, south)
		lat, lon := inverseTM(e, n, zone, south)
		e2, n2 := forwardTM(lat, lon, zone, south)
		if math.Abs(e2-e) > 1e-7 || math.Abs(n2-n) > 1e-7 {
			t.Fatalf("UTM inverse round trip (%v, %v): dE=%.3g dN=%.3g", tc.lat, tc.lon, e2-e, n2-n)
		}
	}

	upsCases := []struct {
		lat   float64
		lon   float64
		north bool
	}{
		{89.999999, 0, true},
		{85, -120, true},
		{84, 179.999999, true},
		{-80.000001, -179.999999, false},
		{-85, 77.85, false},
		{-89.999999, 45, false},
	}
	for _, tc := range upsCases {
		e, n := forwardUPS(tc.lat, tc.lon, tc.north)
		lat, lon := inverseUPS(e, n, tc.north)
		e2, n2 := forwardUPS(lat, lon, tc.north)
		if math.Abs(e2-e) > 1e-7 || math.Abs(n2-n) > 1e-7 {
			t.Fatalf("UPS inverse round trip (%v, %v): dE=%.3g dN=%.3g", tc.lat, tc.lon, e2-e, n2-n)
		}
	}
}
