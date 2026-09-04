// SPDX-License-Identifier: 0BSD

package geoparse

import (
	"math"
	"testing"
)

// Oracle: Format then Parse of a finite WGS84 point must recover the same
// coordinates within the format's expected tolerance.
func TestOracleFormatParseRoundTrip(t *testing.T) {
	cases := []struct {
		name   string
		lat    float64
		lon    float64
		format string
		tol    float64
	}{
		{"wgs84_nairobi", -1.286386, 36.817223, "wgs84", 1e-6},
		{"utm_nl", 52.658, 5.892, "utm", 0.002},
		{"mgrs_nl", 52.658, 5.892, "mgrs", 0.002},
		{"olc_nairobi", -1.286386, 36.817223, "olc", 0.02},
		{"utm_equator", 0.1, 0.1, "utm", 0.002},
		{"mgrs_negative_lon", 40.0, -74.0, "mgrs", 0.002},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			text, _, err := Format(tc.lat, tc.lon, tc.format, false, 0, 0, 10)
			if err != nil {
				t.Fatalf("format: %v", err)
			}
			if text == "" {
				t.Fatal("empty format text")
			}
			got, err := Parse(text, false, 0, 0)
			if err != nil {
				t.Fatalf("parse %q: %v", text, err)
			}
			if math.Abs(got.Lat-tc.lat) > tc.tol || math.Abs(got.Lon-tc.lon) > tc.tol {
				t.Fatalf("roundtrip mismatch format=%s text=%q got=(%v,%v) want=(%v,%v)",
					tc.format, text, got.Lat, got.Lon, tc.lat, tc.lon)
			}
		})
	}
}

// Oracle: reject inputs that must never parse as coordinates.
func TestOracleParseReject(t *testing.T) {
	rejects := []string{
		"",
		"   ",
		"test search",
		"Berlin",
		"hello+world",
		"999, 999",
		"91.0, 0.0",
		"-91.0, 0.0",
		"0.0, 181.0",
		"not-a-mgrs",
	}
	for _, raw := range rejects {
		_, err := Parse(raw, false, 0, 0)
		if err == nil {
			t.Fatalf("expected reject for %q", raw)
		}
	}
}

// Oracle: short Plus Codes require a reference, full codes do not.
func TestOracleShortPlusCodeNeedsRef(t *testing.T) {
	full := "6GCRPR78+CV"
	r, err := Parse(full, false, 0, 0)
	if err != nil {
		t.Fatalf("full code: %v", err)
	}
	if r.Kind != "olc" {
		t.Fatalf("kind %q", r.Kind)
	}

	short, _, err := Format(r.Lat, r.Lon, "olc", true, r.Lat, r.Lon, 10)
	if err != nil {
		t.Fatalf("shorten: %v", err)
	}
	if short == "" || short == full {
		t.Fatalf("expected shortened code, got %q", short)
	}

	_, err = Parse(short, false, 0, 0)
	if err == nil {
		t.Fatalf("short code without ref must reject, got accepted for %q", short)
	}

	got, err := Parse(short, true, r.Lat, r.Lon)
	if err != nil {
		t.Fatalf("short with ref: %v", err)
	}
	if math.Abs(got.Lat-r.Lat) > 0.02 || math.Abs(got.Lon-r.Lon) > 0.02 {
		t.Fatalf("recovered (%v,%v) vs (%v,%v)", got.Lat, got.Lon, r.Lat, r.Lon)
	}
}

// Oracle: unknown format names must fail closed.
func TestOracleUnknownFormatReject(t *testing.T) {
	_, _, err := Format(1, 2, "webmercator", false, 0, 0, 0)
	if err == nil {
		t.Fatal("expected unknown format reject")
	}
}
