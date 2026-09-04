// SPDX-License-Identifier: 0BSD

// Package geoparse auto-detects WGS84, UTM/UPS, MGRS, and OLC text.
package geoparse

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/Quad4-Software/MeshChatX/geo-wasm/mgrs"
	"github.com/Quad4-Software/MeshChatX/geo-wasm/olc"
)

// Result is a parsed geographic point.
type Result struct {
	Lat  float64
	Lon  float64
	Kind string
}

// Parse detects coordinate text. Short Plus Codes need hasRef + refLat/refLon.
func Parse(text string, hasRef bool, refLat, refLon float64) (Result, error) {
	raw := strings.TrimSpace(text)
	if raw == "" {
		return Result{}, fmt.Errorf("empty text")
	}

	if lat, lon, ok := tryParseWGS84(raw); ok {
		return Result{Lat: lat, Lon: lon, Kind: "wgs84"}, nil
	}
	if lat, lon, ok := tryParseUTM(raw); ok {
		return Result{Lat: lat, Lon: lon, Kind: "utm"}, nil
	}

	compact := strings.ReplaceAll(raw, " ", "")
	if olc.IsFull(raw) || olc.IsFull(compact) {
		code := raw
		if !olc.IsFull(raw) {
			code = compact
		}
		area, err := olc.Decode(code)
		if err != nil {
			return Result{}, err
		}
		lat, lon := area.Center()
		return Result{Lat: lat, Lon: lon, Kind: "olc"}, nil
	}
	if olc.IsShort(raw) || olc.IsShort(compact) {
		if !hasRef {
			return Result{}, fmt.Errorf("short plus code needs a reference location")
		}
		code := raw
		if !olc.IsShort(raw) {
			code = compact
		}
		full, err := olc.RecoverNearest(code, refLat, refLon)
		if err != nil {
			return Result{}, err
		}
		area, err := olc.Decode(full)
		if err != nil {
			return Result{}, err
		}
		lat, lon := area.Center()
		return Result{Lat: lat, Lon: lon, Kind: "olc"}, nil
	}

	if pt, err := mgrs.Decode(raw, true); err == nil {
		return Result{Lat: pt.Lat, Lon: pt.Lon, Kind: "mgrs"}, nil
	}
	if pt, err := mgrs.Decode(compact, true); err == nil {
		return Result{Lat: pt.Lat, Lon: pt.Lon, Kind: "mgrs"}, nil
	}

	return Result{}, fmt.Errorf("unrecognized coordinate text")
}

// Format builds a display string for the selected format.
func Format(lat, lon float64, format string, hasRef bool, refLat, refLon float64, codeLen int) (text string, extra map[string]any, err error) {
	extra = map[string]any{}
	switch strings.ToLower(strings.TrimSpace(format)) {
	case "", "wgs84":
		return fmt.Sprintf("%.6f, %.6f", lat, lon), extra, nil
	case "utm":
		g, e := mgrs.LatLonToGrid(lat, lon)
		if e != nil {
			return "", nil, e
		}
		hemi := "S"
		if g.North {
			hemi = "N"
		}
		extra["zone"] = g.Zone
		extra["north"] = g.North
		extra["easting"] = g.Easting
		extra["northing"] = g.Northing
		if g.Zone == mgrs.ZoneUPS {
			return fmt.Sprintf("UPS %s %.0fE %.0fN", hemi, g.Easting, g.Northing), extra, nil
		}
		return fmt.Sprintf("%d%s %.0fE %.0fN", g.Zone, hemi, g.Easting, g.Northing), extra, nil
	case "mgrs":
		ref, e := mgrs.Encode(lat, lon, mgrs.DefaultDigitPairs)
		if e != nil {
			return "", nil, e
		}
		spaced, e := mgrs.FormatSpaced(ref)
		if e != nil {
			spaced = ref
		}
		extra["compact"] = ref
		return spaced, extra, nil
	case "olc":
		if codeLen <= 0 {
			codeLen = 10
		}
		code := olc.Encode(lat, lon, codeLen)
		extra["full"] = code
		text = code
		if hasRef {
			if short, e := olc.Shorten(code, refLat, refLon); e == nil && short != "" {
				text = short
			}
		}
		return text, extra, nil
	default:
		return "", nil, fmt.Errorf("unknown format")
	}
}

func tryParseWGS84(raw string) (lat, lon float64, ok bool) {
	cleaned := strings.ReplaceAll(raw, ",", " ")
	parts := strings.Fields(cleaned)
	if len(parts) != 2 {
		return 0, 0, false
	}
	lat, err1 := strconv.ParseFloat(parts[0], 64)
	lon, err2 := strconv.ParseFloat(parts[1], 64)
	if err1 != nil || err2 != nil {
		return 0, 0, false
	}
	if lat < -90 || lat > 90 || lon < -180 || lon > 180 {
		return 0, 0, false
	}
	return lat, lon, true
}

func tryParseUTM(raw string) (lat, lon float64, ok bool) {
	upper := strings.ToUpper(strings.TrimSpace(raw))
	upper = strings.ReplaceAll(upper, ",", " ")
	fields := strings.Fields(upper)
	if len(fields) == 0 {
		return 0, 0, false
	}
	if fields[0] == "UTM" {
		fields = fields[1:]
	}

	if len(fields) >= 1 && fields[0] == "UPS" {
		return parseUPS(fields[1:])
	}
	if len(fields) < 3 {
		return 0, 0, false
	}

	zoneStr := fields[0]
	hemi := true
	zone := 0
	var err error

	if len(zoneStr) >= 2 {
		last := zoneStr[len(zoneStr)-1]
		if last >= 'A' && last <= 'Z' && last != 'E' {
			hemi = last != 'S'
			zone, err = strconv.Atoi(zoneStr[:len(zoneStr)-1])
		} else {
			zone, err = strconv.Atoi(zoneStr)
		}
	} else {
		zone, err = strconv.Atoi(zoneStr)
	}
	if err != nil || zone < 1 || zone > 60 {
		return 0, 0, false
	}

	idx := 1
	if fields[idx] == "N" || fields[idx] == "S" {
		hemi = fields[idx] == "N"
		idx++
	}
	if len(fields) < idx+2 {
		return 0, 0, false
	}
	easting, e1 := parseMetreToken(fields[idx])
	northing, e2 := parseMetreToken(fields[idx+1])
	if e1 != nil || e2 != nil {
		return 0, 0, false
	}
	pt, err := mgrs.GridToLatLon(mgrs.Grid{
		Zone: zone, North: hemi, Easting: easting, Northing: northing,
	})
	if err != nil {
		return 0, 0, false
	}
	return pt.Lat, pt.Lon, true
}

func parseUPS(fields []string) (lat, lon float64, ok bool) {
	if len(fields) < 3 {
		return 0, 0, false
	}
	north := true
	idx := 0
	if fields[0] == "N" || fields[0] == "S" {
		north = fields[0] == "N"
		idx = 1
	}
	if len(fields) < idx+2 {
		return 0, 0, false
	}
	easting, e1 := parseMetreToken(fields[idx])
	northing, e2 := parseMetreToken(fields[idx+1])
	if e1 != nil || e2 != nil {
		return 0, 0, false
	}
	pt, err := mgrs.GridToLatLon(mgrs.Grid{
		Zone: mgrs.ZoneUPS, North: north, Easting: easting, Northing: northing,
	})
	if err != nil {
		return 0, 0, false
	}
	return pt.Lat, pt.Lon, true
}

func parseMetreToken(tok string) (float64, error) {
	t := strings.TrimSpace(tok)
	t = strings.TrimSuffix(t, "E")
	t = strings.TrimSuffix(t, "N")
	t = strings.TrimSuffix(t, "M")
	return strconv.ParseFloat(t, 64)
}
