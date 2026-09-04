package mgrs

import (
	"math"
	"testing"
)

func dms(latDeg, latMin, latSec float64, lonDeg, lonMin, lonSec float64, lonWest bool) (lat float64, lon float64) {
	lat = latDeg + latMin/60.0 + latSec/3600.0
	lonMag := lonDeg + lonMin/60.0 + lonSec/3600.0
	if lonWest {
		lon = -lonMag
	} else {
		lon = lonMag
	}
	return lat, lon
}

func TestDecode_BlueMarblePublishedMGRS(t *testing.T) {
	const catalog = "19TDJ3858897366"

	latLit, lonLit := dms(44, 13, 36.96, 69, 46, 8.11, true)
	pt, err := Decode(catalog, false)
	if err != nil {
		t.Fatal(err)
	}

	const metreEquivalentLat = 1.0 / 111_111.0
	latTol := 2 * metreEquivalentLat
	lonTol := 2 * metreEquivalentLat / math.Cos(latLit*degRad)

	if math.Abs(pt.Lat-latLit) > latTol || math.Abs(pt.Lon-lonLit) > lonTol {
		t.Fatalf(
			"decoded catalog coordinate outside expected literature tolerance\n"+
				"literal lat/lon %.9f %.9f\n"+
				"decode  %.9f %.9f\n"+
				"Δ lat %.3e Δ lon %.3e\n"+
				"catalog tail resolution is metres; Snyder-class TM introduces a few-metre skew vs some tools",
			latLit, lonLit, pt.Lat, pt.Lon, pt.Lat-latLit, pt.Lon-lonLit)
	}
}

func TestEncodeRoundTripPublicationPoint(t *testing.T) {
	latLit, lonLit := dms(44, 13, 36.96, 69, 46, 8.11, true)
	s, err := Encode(latLit, lonLit, DefaultDigitPairs)
	if err != nil {
		t.Fatal(err)
	}
	pt, err := Decode(s, false)
	if err != nil {
		t.Fatalf("Decode(%s): %v", s, err)
	}

	latTol := 5 * (1.0 / 111_111.0)

	lonTol := latTol / math.Cos(latLit*degRad)

	if math.Abs(pt.Lat-latLit) > latTol || math.Abs(pt.Lon-lonLit) > lonTol {
		t.Fatalf(
			"round trip error too wide for publication point:\n"+
				"want lat/lon %.9f %.9f\n"+
				"got  %.9f %.9f\n"+
				"mgrs %q",

			latLit, lonLit,

			pt.Lat, pt.Lon,

			s,
		)
	}
}

func TestRoundTripRegionalSamples(t *testing.T) {
	points := []struct {
		name string

		lat float64

		lon float64
	}{
		{"western-europe-greenwich", 51.478, -0.0015},

		{"western-us", 39.7392, -104.9903},

		{"oceania", -37.8136, 144.9631},

		{"brazil", -22.9519, -43.2105},

		{"north-norway", 71.1699, 25.7836},
	}

	for _, row := range points {
		t.Run(row.name, func(t *testing.T) {
			latTol := 4 * (1.0 / 111_111.0)

			cosClamp := math.Max(math.Abs(math.Cos(row.lat*degRad)), 1e-3)
			lonTol := latTol / cosClamp
			s, err := Encode(row.lat, row.lon, DefaultDigitPairs)
			if err != nil {
				t.Fatalf("Encode: %v", err)
			}
			pt, err := Decode(s, false)
			if err != nil {
				t.Fatalf("Decode(%q): %v", s, err)
			}

			dLat := pt.Lat - row.lat

			dLon := pt.Lon - row.lon

			if math.Abs(dLat) > latTol || math.Abs(dLon) > lonTol {
				t.Fatalf(
					"round-trip exceeded tolerance (%s):\n"+
						"in  %.9f, %.9f\nout %.9f, %.9f\nΔ lat %.4e Δ lon %.4e\nmgrs=%q",
					row.name,
					row.lat, row.lon,
					pt.Lat, pt.Lon,
					dLat, dLon,
					s,
				)
			}
		})
	}
}

func TestLongitudeZoneOverrides(t *testing.T) {
	rows := []struct {
		name string

		lat float64

		lon float64

		want int

		wantErr bool
	}{
		{"standard-zone", 0, 10, 32, false},

		{"norway-expanded", 60, 4, 32, false},

		{"svalbard-strip-west", 75, 12, 33, false},

		{"polar-too-south", -81, 0, 0, true},
	}

	for _, row := range rows {
		t.Run(row.name, func(t *testing.T) {
			got, err := LongitudeZone(row.lat, row.lon)

			if row.wantErr {

				if err == nil {
					t.Fatal("expected error")
				}

				return

			}

			if err != nil {
				t.Fatal(err)
			}

			if got != row.want {
				t.Fatalf("zone got %d want %d", got, row.want)
			}
		})
	}
}
