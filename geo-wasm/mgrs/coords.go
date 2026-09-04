package mgrs

import "math"

// GeographicLib CheckCoords eps: smallest length s.t. 1e7 - eps < 1e7.
const coordBoundaryEps = 1.0 / (1 << 28) // ~3.7 nm, float64-safe upper-bound nudge

var (
	minEastingIdx  = [4]int{minUPSSind, minUPSNind, minUTMCols, minUTMCols}
	maxEastingIdx  = [4]int{maxUPSSind, maxUPSNind, maxUTMCols, maxUTMCols}
	minNorthingIdx = [4]int{minUPSSind, minUPSNind, minUTMsRowTiles, minUTMsRowTiles - (maxUTMsRowTiles - minUTMnRowTiles)}
	maxNorthingIdx = [4]int{maxUPSSind, maxUPSNind, maxUTMnRowTiles + (maxUTMsRowTiles - minUTMnRowTiles), maxUTMnRowTiles}
)

// checkCoords applies GeographicLib MGRS::CheckCoords rules: closed/open 100 km
// limits, ~4 nm nudge on exact upper edges, and UTM northing hemisphere fold.
func checkCoords(utm bool, north *bool, x, y *float64) error {
	ix := int(math.Floor(*x / mgrsTileSize))
	iy := int(math.Floor(*y / mgrsTileSize))
	ind := 0
	if utm {
		ind = 2
	}
	if *north {
		ind++
	}

	if ix < minEastingIdx[ind] || ix >= maxEastingIdx[ind] {
		if ix == maxEastingIdx[ind] && *x == float64(maxEastingIdx[ind])*mgrsTileSize {
			*x -= coordBoundaryEps
		} else {
			return ErrInvalidGrid
		}
	}
	if iy < minNorthingIdx[ind] || iy >= maxNorthingIdx[ind] {
		if iy == maxNorthingIdx[ind] && *y == float64(maxNorthingIdx[ind])*mgrsTileSize {
			*y -= coordBoundaryEps
			iy = int(math.Floor(*y / mgrsTileSize))
		} else {
			return ErrInvalidGrid
		}
	}

	if !utm {
		return nil
	}
	if *north && iy < minUTMnRowTiles {
		*north = false
		*y += float64(utmNorthernShift)
	} else if !*north && iy >= maxUTMsRowTiles {
		if *y == float64(maxUTMsRowTiles)*mgrsTileSize {
			*y -= coordBoundaryEps
		} else {
			*north = true
			*y -= float64(utmNorthernShift)
		}
	}
	return nil
}
