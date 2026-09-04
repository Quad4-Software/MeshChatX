package mgrs

func stringIndexASCII(s string, needle byte) int {
	for i := 0; i < len(s); i++ {
		if s[i] == needle {
			return i
		}
	}
	return -1
}

func byteIndexASCII(chars []byte, c byte) int {
	for i, v := range chars {
		if v == c {
			return i
		}
	}
	return -1
}

func parseDigit(b byte) (int, bool) {
	switch {
	case b >= '0' && b <= '9':
		return int(b - '0'), true
	default:
		return 0, false
	}
}

func parseZonePrefix(buf []byte) (zone int, used int, err error) {
	if len(buf) == 0 {
		return 0, 0, ErrInvalidMGRS
	}
	z0, ok := parseDigit(buf[0])
	if !ok || z0 == 0 {
		return 0, 0, ErrInvalidMGRS
	}
	zone = z0
	used = 1
	if used < len(buf) {
		if z1, ok := parseDigit(buf[used]); ok {
			next := zone*10 + z1
			if next > 60 {
				return 0, 0, ErrInvalidMGRS
			}
			zone = next
			used = 2
		}
	}
	if zone < 1 || zone > 60 {
		return 0, 0, ErrInvalidMGRS
	}
	return zone, used, nil
}

func compactUpperASCIIFromString(ref string) []byte {
	out := make([]byte, 0, len(ref))
	for i := 0; i < len(ref); i++ {
		ch := ref[i]
		switch ch {
		case ' ', '\t', '\n', '\r':
			continue
		default:
			if ch >= 'a' && ch <= 'z' {
				ch -= 'a' - 'A'
			}
			out = append(out, ch)
		}
	}
	return out
}

func decodeNormalizedParts(data []byte, centerCell bool) (Parts, error) {
	if len(data) == 0 {
		return Parts{}, ErrInvalidMGRS
	}
	if data[0] >= '0' && data[0] <= '9' {
		return decodeUTMNormalized(data, centerCell)
	}
	return decodeUPSNormalized(data, centerCell)
}

func decodeUTMNormalized(data []byte, centerCell bool) (Parts, error) {
	zone, used, err := parseZonePrefix(data)
	if err != nil {
		return Parts{}, err
	}
	idx := used
	if idx >= len(data) {
		return Parts{}, ErrInvalidMGRS
	}

	bandLUT := byteIndexASCII(latBand, data[idx])
	if bandLUT < 0 {
		return Parts{}, ErrInvalidMGRS
	}
	band := data[idx]
	idx++
	northp := bandLUT >= 10

	if idx+2 > len(data) {
		return Parts{}, ErrInvalidMGRS
	}

	colLetter := data[idx]
	col := stringIndexASCII(utmcols[(zone-1)%3], colLetter)
	if col < 0 {
		return Parts{}, ErrInvalidMGRS
	}
	idx++

	rowLetter := data[idx]
	rowPeriodic := byteIndexASCII(utmrows, rowLetter)
	if rowPeriodic < 0 {
		return Parts{}, ErrInvalidMGRS
	}
	idx++

	iRow := rowPeriodic
	if (zone-1)&1 != 0 {
		iRow = posMod(iRow+(utmerowPeriod-utmevenRowShift), utmerowPeriod)
	}

	iBand := bandLUT - 10
	rowTiles := utmRow(iBand, col, iRow)
	if rowTiles == maxUTMsRowTiles {
		return Parts{}, ErrInvalidGridSquareBand
	}
	if !northp {
		rowTiles += 100
	}

	e100k := col + minUTMCols
	tail := data[idx:]
	easting, northing, pairs, err := metresFromDigitTail(tail, e100k, rowTiles, centerCell)
	if err != nil {
		return Parts{}, err
	}
	latDeg, lonDeg := inverseTM(easting, northing, zone, !northp)
	return Parts{
		Zone:       zone,
		North:      northp,
		Band:       band,
		Col:        colLetter,
		Row:        rowLetter,
		DigitPairs: pairs,
		Easting:    easting,
		Northing:   northing,
		Point:      Point{Lat: latDeg, Lon: lonDeg},
	}, nil
}
