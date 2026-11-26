package mgrs

import (
	"bytes"
	"fmt"
	"math"
	"math/rand"
	"os/exec"
	"strconv"
	"strings"
	"testing"
)

// geoConvertPrec maps our digit-pair count to GeoConvert -p.
// GeographicLib uses digits_per_coord = 5 + prec for MGRS.
func geoConvertPrec(digitPairs int) int {
	return digitPairs - 5
}

func runGeoConvert(t *testing.T, path string, args []string, stdin string) string {
	t.Helper()
	cmd := exec.Command(path, args...)
	cmd.Stdin = strings.NewReader(stdin)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		t.Fatalf("GeoConvert %v: %v\nstdout=%q\nstderr=%q", args, err, stdout.String(), stderr.String())
	}
	return strings.TrimSpace(stdout.String())
}

func TestGeoLibEncodeMatchesGeoConvert(t *testing.T) {
	path := requireTool(t, "GeoConvert")
	cases := []struct {
		name     string
		lat, lon float64
		pairs    int
	}{
		{"europe", 52.658, 5.892, 5},
		{"antarctic-ups", -85, 77.85, 5},
		{"arctic-ups", 85, 0, 5},
		{"norway-zone", 60, 4, 5},
		{"svalbard-zone", 75, 12, 5},
		{"blue-marble-point", 44.226933333333335, -69.76891944444445, 5},
		{"equator", 0, 0, 5},
		{"melbourne", -37.8136, 144.9631, 5},
		{"baghdad-1km", 33.33424, 44.40363, 2},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			out := runGeoConvert(t, path,
				[]string{"-m", "-p", strconv.Itoa(geoConvertPrec(tc.pairs))},
				fmt.Sprintf("%.15f %.15f\n", tc.lat, tc.lon),
			)
			want := strings.ReplaceAll(out, " ", "")
			got, err := Encode(tc.lat, tc.lon, tc.pairs)
			if err != nil {
				t.Fatal(err)
			}
			if got != want {
				t.Fatalf("got %q want GeoConvert %q", got, want)
			}
		})
	}
}

func TestGeoLibRandomBatchMatchesGeoConvert(t *testing.T) {
	path := requireTool(t, "GeoConvert")
	rng := rand.New(rand.NewSource(20261125))
	for _, pairs := range []int{0, 2, 5, 8} {
		t.Run(fmt.Sprintf("pairs-%d", pairs), func(t *testing.T) {
			const count = 200
			pts := make([][2]float64, 0, count)
			var in strings.Builder
			for len(pts) < count {
				lat := -90 + rng.Float64()*180
				lon := -180 + rng.Float64()*360
				pts = append(pts, [2]float64{lat, lon})
				fmt.Fprintf(&in, "%.15f %.15f\n", lat, lon)
			}
			out := runGeoConvert(t, path,
				[]string{"-m", "-p", strconv.Itoa(geoConvertPrec(pairs))},
				in.String(),
			)
			lines := strings.Split(strings.TrimSpace(out), "\n")
			if len(lines) != count {
				t.Fatalf("GeoConvert returned %d lines, want %d", len(lines), count)
			}
			mismatches := 0
			for i, pt := range pts {
				got, err := Encode(pt[0], pt[1], pairs)
				if err != nil {
					t.Errorf("point %d Encode error: %v", i, err)
					continue
				}
				want := strings.ReplaceAll(strings.TrimSpace(lines[i]), " ", "")
				if got != want {
					mismatches++
					if mismatches <= 5 {
						t.Errorf("point %d %.15f %.15f got %s want %s", i, pt[0], pt[1], got, want)
					}
				}
			}
			if mismatches != 0 {
				t.Fatalf("%d of %d references mismatched", mismatches, count)
			}
		})
	}
}

func TestGeoLibRandomGridMatchesGeoConvert(t *testing.T) {
	path := requireTool(t, "GeoConvert")
	rng := rand.New(rand.NewSource(20261126))
	const count = 300
	pts := make([][2]float64, 0, count)
	var in strings.Builder
	for len(pts) < count {
		lat := -90 + rng.Float64()*180
		lon := -180 + rng.Float64()*360
		pts = append(pts, [2]float64{lat, lon})
		fmt.Fprintf(&in, "%.15f %.15f\n", lat, lon)
	}
	out := runGeoConvert(t, path, []string{"-u", "-p", "12"}, in.String())
	lines := strings.Split(strings.TrimSpace(out), "\n")
	if len(lines) != count {
		t.Fatalf("GeoConvert returned %d lines, want %d", len(lines), count)
	}
	const tolM = 5e-9
	for i, pt := range pts {
		fields := strings.Fields(lines[i])
		if len(fields) != 3 {
			t.Fatalf("point %d unexpected GeoConvert output %q", i, lines[i])
		}
		wantZone := ZoneUPS
		wantNorth := fields[0][0] == 'n'
		if fields[0] != "n" && fields[0] != "s" {
			if _, err := fmt.Sscanf(fields[0][:len(fields[0])-1], "%d", &wantZone); err != nil {
				t.Fatalf("point %d parse zone %q: %v", i, fields[0], err)
			}
			wantNorth = fields[0][len(fields[0])-1] == 'n'
		}
		var wantE, wantN float64
		if _, err := fmt.Sscanf(fields[1], "%f", &wantE); err != nil {
			t.Fatalf("point %d parse easting: %v", i, err)
		}
		if _, err := fmt.Sscanf(fields[2], "%f", &wantN); err != nil {
			t.Fatalf("point %d parse northing: %v", i, err)
		}

		got, err := LatLonToGrid(pt[0], pt[1])
		if err != nil {
			t.Errorf("point %d LatLonToGrid error: %v", i, err)
			continue
		}
		if got.Zone != wantZone || got.North != wantNorth {
			t.Errorf("point %d grid zone = %d/%v, want %d/%v", i, got.Zone, got.North, wantZone, wantNorth)
			continue
		}
		if math.Abs(got.Easting-wantE) > tolM || math.Abs(got.Northing-wantN) > tolM {
			t.Errorf("point %d %.15f %.15f grid %.12f %.12f want %.12f %.12f",
				i, pt[0], pt[1], got.Easting, got.Northing, wantE, wantN)
		}
	}
}

func TestGeoLibRandomDecodeMatchesGeoConvert(t *testing.T) {
	path := requireTool(t, "GeoConvert")
	rng := rand.New(rand.NewSource(20261127))
	const count = 300
	var encodeIn strings.Builder
	for range count {
		fmt.Fprintf(&encodeIn, "%.15f %.15f\n", -90+rng.Float64()*180, -180+rng.Float64()*360)
	}
	encoded := runGeoConvert(t, path,
		[]string{"-m", "-p", strconv.Itoa(geoConvertPrec(DefaultDigitPairs))},
		encodeIn.String(),
	)
	refs := strings.Split(strings.TrimSpace(encoded), "\n")
	if len(refs) != count {
		t.Fatalf("GeoConvert returned %d references, want %d", len(refs), count)
	}
	decoded := runGeoConvert(t, path, []string{"-g", "-p", "15"}, strings.Join(refs, "\n")+"\n")
	lines := strings.Split(strings.TrimSpace(decoded), "\n")
	if len(lines) != count {
		t.Fatalf("GeoConvert returned %d decode lines, want %d", len(lines), count)
	}
	const tolDeg = 5e-13
	for i, ref := range refs {
		compact := strings.ReplaceAll(strings.TrimSpace(ref), " ", "")
		fields := strings.Fields(lines[i])
		if len(fields) < 2 {
			t.Fatalf("reference %d unexpected GeoConvert decode %q", i, lines[i])
		}
		var wantLat, wantLon float64
		if _, err := fmt.Sscanf(fields[0], "%f", &wantLat); err != nil {
			t.Fatalf("reference %d parse latitude: %v", i, err)
		}
		if _, err := fmt.Sscanf(fields[1], "%f", &wantLon); err != nil {
			t.Fatalf("reference %d parse longitude: %v", i, err)
		}
		got, err := Decode(compact, true)
		if err != nil {
			t.Errorf("reference %d %s Decode error: %v", i, compact, err)
			continue
		}
		dLon := math.Abs(got.Lon - wantLon)
		if dLon > 180 {
			dLon = 360 - dLon
		}
		if math.Abs(got.Lat-wantLat) > tolDeg || dLon > tolDeg {
			t.Errorf("reference %d %s decode %.12f %.12f want %.12f %.12f",
				i, compact, got.Lat, got.Lon, wantLat, wantLon)
		}
	}
}

func TestGeoLibDecodeCentreMatchesGeoConvert(t *testing.T) {
	path := requireTool(t, "GeoConvert")
	refs := []string{
		"31UFU9559138152",
		"BHP4301516908",
		"38SMB4488",
		"19TDJ3858797365",
	}
	for _, ref := range refs {
		t.Run(ref, func(t *testing.T) {
			out := runGeoConvert(t, path, []string{"-g", "-p", "9"}, ref+"\n")
			fields := strings.Fields(out)
			if len(fields) < 2 {
				t.Fatalf("unexpected GeoConvert output %q", out)
			}
			var lat, lon float64
			if _, err := fmt.Sscanf(fields[0], "%f", &lat); err != nil {
				t.Fatal(err)
			}
			if _, err := fmt.Sscanf(fields[1], "%f", &lon); err != nil {
				t.Fatal(err)
			}
			pt, err := Decode(ref, true)
			if err != nil {
				t.Fatal(err)
			}
			const tolDeg = 2e-5
			if math.Abs(pt.Lat-lat) > tolDeg || math.Abs(pt.Lon-lon) > tolDeg {
				t.Fatalf("decode centre vs GeoConvert\nlib  %.9f %.9f\ngeolib %.9f %.9f",
					pt.Lat, pt.Lon, lat, lon)
			}
		})
	}
}
