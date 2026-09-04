package mgrs

func encodeUPSInto(dst []byte, north bool, easting, northing float64, digitPairs int) ([]byte, error) {
	if digitPairs < 0 || digitPairs > MaxDigitPairs {
		return nil, ErrInvalidDigitPairs
	}
	xh, yh := eastNorthTileIndices(easting, northing)
	eastp := xh >= upsEasting
	iband := 0
	if north {
		iband = 2
	}
	if eastp {
		iband++
	}
	colLetters := upscols[iband]
	rowLetters := upsrows[0]
	if north {
		rowLetters = upsrows[1]
	}
	var colBase int
	switch {
	case eastp:
		colBase = upsEasting
	case north:
		colBase = minUPSNind
	default:
		colBase = minUPSSind
	}
	rowBase := minUPSSind
	if north {
		rowBase = minUPSNind
	}
	icol := xh - colBase
	irow := yh - rowBase
	if icol < 0 || icol >= len(colLetters) || irow < 0 || irow >= len(rowLetters) {
		return nil, ErrInvalidGridSquareBand
	}

	n := encodedLen(ZoneUPS, digitPairs)
	base := len(dst)
	dst = growDst(dst, n)
	out := dst[base : base+n]
	out[0] = upsband[iband]
	out[1] = colLetters[icol]
	out[2] = rowLetters[irow]
	writeDigitTail(out, 3, digitPairs, easting, northing, xh, yh)
	if digitPairs == 0 {
		return dst[:base+3], nil
	}
	return dst, nil
}
