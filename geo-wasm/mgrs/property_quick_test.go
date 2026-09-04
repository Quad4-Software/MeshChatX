package mgrs

import (
	"math"
	"testing"
	"testing/quick"
)

func TestPropertyEncodeDecodeRoundtripWithinTolerance(t *testing.T) {
	const degLatTol = 1e-2
	cfg := quick.Config{MaxCount: 450}
	fn := func(lat, lon float64) bool {
		switch {
		case math.IsNaN(lat) || math.IsNaN(lon) || math.IsInf(lat, 0) || math.IsInf(lon, 0):
			return true
		default:
			if lat < -90 || lat > 90 {
				return true
			}
			if lon < -180 || lon > 180 {
				return true
			}
			s, err := Encode(lat, lon, DefaultDigitPairs)
			if err != nil {
				return false
			}
			pt, err := Decode(s, true)
			if err != nil {
				return false
			}
			clat := math.Max(math.Abs(math.Cos(lat*degRad)), 1e-3)
			lonTol := degLatTol / clat
			return math.Abs(pt.Lat-lat) <= degLatTol && math.Abs(pt.Lon-lon) <= lonTol
		}
	}
	if err := quick.Check(fn, &cfg); err != nil {
		t.Fatal(err)
	}
}
