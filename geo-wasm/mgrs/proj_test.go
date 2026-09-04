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

func runProjUTM(t *testing.T, projPath string, lon, lat float64, zone int, southern bool) (e, n float64) {
	t.Helper()
	args := []string{"+proj=utm", fmt.Sprintf("+zone=%d", zone), "+datum=WGS84"}
	if southern {
		args = append(args, "+south")
	}
	var buf bytes.Buffer
	fmt.Fprintf(&buf, "%.12f %.12f\n", lon, lat)
	cmd := exec.Command(projPath, args...)
	cmd.Stdin = &buf
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("proj failed: %v", err)
	}
	fields := strings.Fields(string(out))
	if len(fields) < 2 {
		t.Fatalf("unexpected proj output: %q", out)
	}
	east, err1 := strconv.ParseFloat(fields[0], 64)
	north, err2 := strconv.ParseFloat(fields[1], 64)
	if err1 != nil || err2 != nil {
		t.Fatalf("parse proj fields %v: %v %v", fields, err1, err2)
	}
	return east, north
}

func TestProjForwardUTMmatchesLibrary(t *testing.T) {
	projPath := requireTool(t, "proj")
	cases := []struct {
		name     string
		lat, lon float64
	}{
		{"netherlands", 52.658, 5.892},
		{"sydney", -33.8688, 151.2093},
		{"chile", -33.4489, -70.6693},
		{"maine-near-publication", 44.22693333333333, -69.76947527777778},
		{"norway-override", 60, 4},
		{"svalbard-override", 75, 12},
	}
	const metreTol = 0.5
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			zone, zerr := LongitudeZone(tc.lat, tc.lon)
			if zerr != nil {
				t.Fatal(zerr)
			}
			south := tc.lat < 0
			eMine, nMine := forwardTM(tc.lat, tc.lon, zone, south)
			eProj, nProj := runProjUTM(t, projPath, tc.lon, tc.lat, zone, south)
			if math.Abs(eMine-eProj) > metreTol || math.Abs(nMine-nProj) > metreTol {
				t.Fatalf("proj vs library zone=%d south=%v\nlib  E=%.3f N=%.3f\nproj E=%.3f N=%.3f",
					zone, south, eMine, nMine, eProj, nProj)
			}
		})
	}
}
