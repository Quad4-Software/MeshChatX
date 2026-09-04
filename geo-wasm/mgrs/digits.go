package mgrs

import "math"

func growDst(dst []byte, n int) []byte {
	base := len(dst)
	need := base + n
	if cap(dst) < need {
		grow := make([]byte, base, need)
		copy(grow, dst)
		dst = grow
	}
	return dst[:need]
}

func writeDigitTail(out []byte, off, digitPairs int, easting, northing float64, xh, yh int) {
	if digitPairs == 0 {
		return
	}
	ix := int64(math.Floor(easting * coordMultiply))
	iy := int64(math.Floor(northing * coordMultiply))
	ix -= tileScaleMicro * int64(xh)
	iy -= tileScaleMicro * int64(yh)

	divIdx := MaxDigitPairs - digitPairs
	if divIdx < 0 || divIdx >= len(pow10Int64) {
		divIdx = 0
	}
	div := pow10Int64[divIdx]
	if div == 0 {
		div = 1
	}
	ix /= div
	iy /= div

	for i := digitPairs - 1; i >= 0; i-- {
		out[off+i] = digits[ix%mgrsdigitBase]
		ix /= mgrsdigitBase
		out[off+digitPairs+i] = digits[iy%mgrsdigitBase]
		iy /= mgrsdigitBase
	}
}

func encodedPrefixLen(zone int) int {
	if zone == ZoneUPS {
		return 3
	}
	return 5
}

func encodedLen(zone, digitPairs int) int {
	return encodedPrefixLen(zone) + digitPairs*2
}
