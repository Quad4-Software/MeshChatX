// SPDX-License-Identifier: 0BSD

package geoparse

import (
	"math"
	"testing"
)

func TestParseWGS84(t *testing.T) {
	r, err := Parse("-1.286386, 36.817223", false, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if r.Kind != "wgs84" {
		t.Fatalf("kind %q", r.Kind)
	}
	if math.Abs(r.Lat+1.286386) > 1e-9 || math.Abs(r.Lon-36.817223) > 1e-9 {
		t.Fatalf("got %v %v", r.Lat, r.Lon)
	}
}

func TestParseOLC(t *testing.T) {
	r, err := Parse("6GCRPR78+CV", false, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if r.Kind != "olc" {
		t.Fatalf("kind %q", r.Kind)
	}
	if math.Abs(r.Lat+1.286) > 0.02 || math.Abs(r.Lon-36.817) > 0.02 {
		t.Fatalf("got %v %v", r.Lat, r.Lon)
	}
}

func TestFormatUTMRoundTrip(t *testing.T) {
	text, extra, err := Format(52.658, 5.892, "utm", false, 0, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if text == "" {
		t.Fatal("empty utm text")
	}
	r, err := Parse(text, false, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if math.Abs(r.Lat-52.658) > 0.001 || math.Abs(r.Lon-5.892) > 0.001 {
		t.Fatalf("roundtrip %v %v extra=%v text=%q", r.Lat, r.Lon, extra, text)
	}
}

func TestFormatMGRS(t *testing.T) {
	text, _, err := Format(52.658, 5.892, "mgrs", false, 0, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	r, err := Parse(text, false, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if r.Kind != "mgrs" {
		t.Fatalf("kind %q", r.Kind)
	}
}
