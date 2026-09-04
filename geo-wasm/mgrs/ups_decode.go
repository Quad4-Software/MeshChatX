package mgrs

func decodeUPSNormalized(data []byte, centerCell bool) (Parts, error) {
	if len(data) < 1 {
		return Parts{}, ErrInvalidMGRS
	}
	iband := byteIndexASCII(upsband, data[0])
	if iband < 0 {
		return Parts{}, ErrInvalidMGRS
	}
	northp := iband >= 2
	if len(data) == 1 {
		return Parts{}, ErrInvalidMGRS
	}
	if len(data) < 3 {
		return Parts{}, ErrInvalidMGRS
	}
	colLetters := upscols[iband]
	rowLetters := upsrows[0]
	if northp {
		rowLetters = upsrows[1]
	}
	icol := stringIndexASCII(colLetters, data[1])
	irow := stringIndexASCII(rowLetters, data[2])
	if icol < 0 || irow < 0 {
		return Parts{}, ErrInvalidMGRS
	}
	eastp := iband&1 != 0
	colBase := minUPSSind
	if eastp {
		colBase = upsEasting
	} else if northp {
		colBase = minUPSNind
	}
	rowBase := minUPSSind
	if northp {
		rowBase = minUPSNind
	}
	xh := icol + colBase
	yh := irow + rowBase

	tail := data[3:]
	easting, northing, pairs, err := metresFromDigitTail(tail, xh, yh, centerCell)
	if err != nil {
		return Parts{}, err
	}
	lat, lon := inverseUPS(easting, northing, northp)
	return Parts{
		Zone:       ZoneUPS,
		North:      northp,
		Band:       data[0],
		Col:        data[1],
		Row:        data[2],
		DigitPairs: pairs,
		Easting:    easting,
		Northing:   northing,
		Point:      Point{Lat: lat, Lon: lon},
	}, nil
}
