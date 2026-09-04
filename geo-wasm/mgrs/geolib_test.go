package mgrs

import (
	"bytes"
	"fmt"
	"math"
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
				fmt.Sprintf("%.12f %.12f\n", tc.lat, tc.lon),
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
