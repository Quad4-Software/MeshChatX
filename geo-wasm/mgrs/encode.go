package mgrs

import "math"

// MaxDigitPairs is the finest supported easting+northing pair count encoded in
// the numerical MGRS tail (mirrors GeographicLib permitting sub-metre granularity).
const MaxDigitPairs = 11

const latBandAngeps = 1e-13

func encodeUTMInto(dst []byte, zone int, latDeg float64, north bool, easting, northing float64, digitPairs int) ([]byte, error) {
	if digitPairs < 0 || digitPairs > MaxDigitPairs {
		return nil, ErrInvalidDigitPairs
	}
	if zone < 1 || zone > 60 {
		return nil, ErrInvalidMGRS
	}

	iband := resolveBandIndex(latDeg, north)
	xh, yh := eastNorthTileIndices(easting, northing)
	colLetters := utmcols[(zone-1)%3]
	icol := xh - minUTMCols
	if icol < 0 || icol >= len(colLetters) {
		return nil, ErrInvalidGridSquareBand
	}

	rowPeriodic := posMod(yh, utmerowPeriod)
	iTruth := utmRow(iband, icol, rowPeriodic)
	exp := yTileExpectation(north, yh)
	if iTruth != exp || iTruth == maxUTMsRowTiles {
		return nil, ErrLatitudeCoordsClash
	}

	n := encodedLen(zone, digitPairs)
	base := len(dst)
	dst = growDst(dst, n)
	out := dst[base : base+n]
	out[0] = digits[zone/mgrsdigitBase]
	out[1] = digits[zone%mgrsdigitBase]
	out[2] = latBand[10+iband]
	out[3] = colLetters[icol]
	rowPos := posMod(yh+((zone-1)&1)*utmevenRowShift, utmerowPeriod)
	out[4] = utmrows[rowPos]
	writeDigitTail(out, 5, digitPairs, easting, northing, xh, yh)
	if digitPairs == 0 {
		return dst[:base+5], nil
	}
	return dst, nil
}

func eastNorthTileIndices(easting, northing float64) (xh int, yh int) {
	x := math.Floor(easting * coordMultiply)
	y := math.Floor(northing * coordMultiply)
	return int(int64(x) / tileScaleMicro), int(int64(y) / tileScaleMicro)
}

func yTileExpectation(north bool, yh int) int {
	if north {
		return yh
	}
	return yh - maxUTMsRowTiles
}

func resolveBandIndex(latDeg float64, north bool) int {
	switch {
	case latDeg > -latBandAngeps && latDeg < latBandAngeps:
		if north {
			return 0
		}
		return -1
	default:
		return latitudeBand(latDeg)
	}
}
