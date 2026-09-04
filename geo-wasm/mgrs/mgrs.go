package mgrs

import "math"

// Point expresses a geographic location on WGS84 in decimal degrees.
type Point struct {
	Lat float64
	Lon float64
}

// ZoneUPS is the GeographicLib-style zone number for polar UPS.
const ZoneUPS = 0

// Grid is projected metres in UTM (zone 1-60) or UPS (ZoneUPS).
type Grid struct {
	Zone     int
	North    bool
	Easting  float64
	Northing float64
}

// Parts is a structured MGRS decode result.
type Parts struct {
	Compact    string
	Zone       int
	North      bool
	Band       byte
	Col        byte
	Row        byte
	DigitPairs int
	Easting    float64
	Northing   float64
	Point      Point
}

const (
	DefaultDigitPairs = 5
	MaxEncodedLen     = 5 + MaxDigitPairs*2
)

func LongitudeZone(latDeg, lonDeg float64) (int, error) {
	switch {
	case latDeg < -80 || latDeg >= 84:
		return 0, ErrLatOutOfUTMRange
	default:
		return longitudeZoneStandard(latDeg, lonDeg), nil
	}
}

// LatLonToGrid projects WGS84 lat/lon to UTM or UPS grid metres.
func LatLonToGrid(latDeg, lonDeg float64) (Grid, error) {
	if math.IsNaN(latDeg) || math.IsNaN(lonDeg) || math.IsInf(latDeg, 0) || math.IsInf(lonDeg, 0) {
		return Grid{}, ErrInvalidGrid
	}
	if latDeg < -90 || latDeg > 90 {
		return Grid{}, ErrInvalidGrid
	}
	if latDeg < -80 || latDeg >= 84 {
		north := latDeg >= 0
		e, n := forwardUPS(latDeg, lonDeg, north)
		return Grid{Zone: ZoneUPS, North: north, Easting: e, Northing: n}, nil
	}
	north := latDeg >= 0
	zone := longitudeZoneStandard(latDeg, lonDeg)
	if zone < 1 || zone > 60 {
		return Grid{}, ErrLatOutOfUTMRange
	}
	e, n := forwardTM(latDeg, lonDeg, zone, !north)
	return Grid{Zone: zone, North: north, Easting: e, Northing: n}, nil
}

// GridToLatLon converts UTM or UPS metres to WGS84 lat/lon.
func GridToLatLon(g Grid) (Point, error) {
	if g.Zone == ZoneUPS {
		lat, lon := inverseUPS(g.Easting, g.Northing, g.North)
		return Point{Lat: lat, Lon: lon}, nil
	}
	if g.Zone < 1 || g.Zone > 60 {
		return Point{}, ErrInvalidGrid
	}
	lat, lon := inverseTM(g.Easting, g.Northing, g.Zone, !g.North)
	return Point{Lat: lat, Lon: lon}, nil
}

func encodeGridInto(dst []byte, g Grid, digitPairs int, latHint float64, haveLat bool) ([]byte, error) {
	if digitPairs < 0 || digitPairs > MaxDigitPairs {
		return nil, ErrInvalidDigitPairs
	}
	north := g.North
	easting := g.Easting
	northing := g.Northing
	utm := g.Zone != ZoneUPS
	if err := checkCoords(utm, &north, &easting, &northing); err != nil {
		return nil, err
	}
	if g.Zone == ZoneUPS {
		return encodeUPSInto(dst, north, easting, northing, digitPairs)
	}
	if g.Zone < 1 || g.Zone > 60 {
		return nil, ErrInvalidGrid
	}
	lat := latHint
	if !haveLat {
		pt, err := GridToLatLon(Grid{Zone: g.Zone, North: north, Easting: easting, Northing: northing})
		if err != nil {
			return nil, err
		}
		lat = pt.Lat
	}
	return encodeUTMInto(dst, g.Zone, lat, north, easting, northing, digitPairs)
}

// EncodeGrid formats a UTM/UPS grid point as a compact MGRS string.
func EncodeGrid(g Grid, digitPairs int) (string, error) {
	buf, err := encodeGridInto(nil, g, digitPairs, 0, false)
	if err != nil {
		return "", err
	}
	return string(buf), nil
}

// EncodeGridBytes is like EncodeGrid but returns ASCII bytes.
func EncodeGridBytes(g Grid, digitPairs int) ([]byte, error) {
	return encodeGridInto(nil, g, digitPairs, 0, false)
}

// EncodeGridTo writes compact MGRS into dst. dst must hold encodedLen bytes.
func EncodeGridTo(dst []byte, g Grid, digitPairs int) (int, error) {
	if digitPairs < 0 || digitPairs > MaxDigitPairs {
		return 0, ErrInvalidDigitPairs
	}
	if g.Zone != ZoneUPS && (g.Zone < 1 || g.Zone > 60) {
		return 0, ErrInvalidGrid
	}
	need := encodedLen(g.Zone, digitPairs)
	if len(dst) < need {
		return 0, ErrShortBuffer
	}
	out, err := encodeGridInto(dst[:0], g, digitPairs, 0, false)
	if err != nil {
		return 0, err
	}
	return len(out), nil
}

// AppendEncodeGrid appends a compact MGRS reference for g onto dst.
func AppendEncodeGrid(dst []byte, g Grid, digitPairs int) ([]byte, error) {
	return encodeGridInto(dst, g, digitPairs, 0, false)
}

func marshalMGRS(latDeg, lonDeg float64, digitPairs int) ([]byte, error) {
	g, err := LatLonToGrid(latDeg, lonDeg)
	if err != nil {
		return nil, err
	}
	return encodeGridInto(nil, g, digitPairs, latDeg, true)
}

func marshalMGRSInto(dst []byte, latDeg, lonDeg float64, digitPairs int) ([]byte, error) {
	g, err := LatLonToGrid(latDeg, lonDeg)
	if err != nil {
		return nil, err
	}
	return encodeGridInto(dst, g, digitPairs, latDeg, true)
}

// Encode formats (latDeg, lonDeg) as an MGRS reference string without spaces.
func Encode(latDeg, lonDeg float64, digitPairs int) (string, error) {
	buf, err := marshalMGRS(latDeg, lonDeg, digitPairs)
	if err != nil {
		return "", err
	}
	return string(buf), nil
}

// EncodeBytes is like Encode but returns the ASCII bytes directly, avoiding an
// extra string allocation when callers need []byte downstream.
func EncodeBytes(latDeg, lonDeg float64, digitPairs int) ([]byte, error) {
	return marshalMGRS(latDeg, lonDeg, digitPairs)
}

// EncodeTo writes an encoded MGRS reference into dst and returns the number of
// bytes written. dst must have length >= MaxEncodedLen for arbitrary zone.
// This allows a zero-allocation encode path when the caller reuses a fixed buffer.
func EncodeTo(dst []byte, latDeg, lonDeg float64, digitPairs int) (int, error) {
	if digitPairs < 0 || digitPairs > MaxDigitPairs {
		return 0, ErrInvalidDigitPairs
	}
	g, err := LatLonToGrid(latDeg, lonDeg)
	if err != nil {
		return 0, err
	}
	need := encodedLen(g.Zone, digitPairs)
	if len(dst) < need {
		return 0, ErrShortBuffer
	}
	out, err := encodeGridInto(dst[:0], g, digitPairs, latDeg, true)
	if err != nil {
		return 0, err
	}
	return len(out), nil
}

// AppendEncode appends a newly encoded reference to dst and returns the
// enlarged slice (convenient for buffering many references with one allocator).
func AppendEncode(dst []byte, latDeg, lonDeg float64, digitPairs int) ([]byte, error) {
	return marshalMGRSInto(dst, latDeg, lonDeg, digitPairs)
}

// Decode converts an MGRS reference to a WGS84 point.
func Decode(reference string, centerCell bool) (Point, error) {
	data := compactUpperASCIIFromString(reference)
	if len(data) == 0 {
		return Point{}, ErrInvalidMGRS
	}
	p, err := decodeNormalizedParts(data, centerCell)
	if err != nil {
		return Point{}, err
	}
	return p.Point, nil
}

// DecodeParts converts an MGRS reference into structured grid and geographic parts.
func DecodeParts(reference string, centerCell bool) (Parts, error) {
	data := compactUpperASCIIFromString(reference)
	if len(data) == 0 {
		return Parts{}, ErrInvalidMGRS
	}
	p, err := decodeNormalizedParts(data, centerCell)
	if err != nil {
		return Parts{}, err
	}
	p.Compact = string(data)
	return p, nil
}
