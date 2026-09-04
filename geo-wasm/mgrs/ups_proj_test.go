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

func runCS2CSUPS(t *testing.T, lon, lat float64, north bool) (e, n float64) {
	t.Helper()
	lat0 := 90
	if !north {
		lat0 = -90
	}
	args := []string{
		"+proj=latlong", "+datum=WGS84", "+to",
		fmt.Sprintf("+proj=stere +lat_0=%d +lat_ts=%d +lon_0=0 +k_0=0.994 +x_0=2000000 +y_0=2000000 +ellps=WGS84", lat0, lat0),
	}
	var buf bytes.Buffer
	fmt.Fprintf(&buf, "%.12f %.12f\n", lon, lat)
	cmd := exec.Command("cs2cs", args...)
	cmd.Stdin = &buf
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("cs2cs failed: %v", err)
	}
	fields := strings.Fields(string(out))
	if len(fields) < 2 {
		t.Fatalf("unexpected cs2cs output: %q", out)
	}
	east, err1 := strconv.ParseFloat(fields[0], 64)
	northing, err2 := strconv.ParseFloat(fields[1], 64)
	if err1 != nil || err2 != nil {
		t.Fatalf("parse cs2cs fields %v: %v %v", fields, err1, err2)
	}
	return east, northing
}

func TestProjForwardUPSmatchesLibrary(t *testing.T) {
	_ = requireTool(t, "cs2cs")
	cases := []struct {
		name     string
		lat, lon float64
		north    bool
	}{
		{"arctic-prime", 85, 0, true},
		{"arctic-ne", 88, 45, true},
		{"antarctic-doc", -85, 77.85, false},
		{"antarctic-west", -82, -60, false},
	}
	const metreTol = 1.0
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			eMine, nMine := forwardUPS(tc.lat, tc.lon, tc.north)
			eProj, nProj := runCS2CSUPS(t, tc.lon, tc.lat, tc.north)
			if math.Abs(eMine-eProj) > metreTol || math.Abs(nMine-nProj) > metreTol {
				t.Fatalf("cs2cs vs library\nlib  E=%.3f N=%.3f\nproj E=%.3f N=%.3f",
					eMine, nMine, eProj, nProj)
			}
		})
	}
}
