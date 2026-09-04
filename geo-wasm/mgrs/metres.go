package mgrs

func metresFromDigitTail(tail []byte, xh, yh int, centerCell bool) (easting, northing float64, pairs int, err error) {
	if len(tail)%2 != 0 {
		return 0, 0, 0, ErrInvalidMGRS
	}
	pairs = len(tail) / 2
	if pairs > MaxDigitPairs {
		return 0, 0, 0, ErrInvalidMGRS
	}
	for _, ch := range tail {
		if ch < '0' || ch > '9' {
			return 0, 0, 0, ErrInvalidMGRS
		}
	}
	scale := float64(1)
	xQty := float64(xh)
	yQty := float64(yh)
	eastDigits := tail[:pairs]
	northDigits := tail[pairs:]
	for i := 0; i < pairs; i++ {
		ed, okE := parseDigit(eastDigits[i])
		nd, okN := parseDigit(northDigits[i])
		if !okE || !okN {
			return 0, 0, 0, ErrInvalidMGRS
		}
		scale *= float64(mgrsdigitBase)
		xQty = float64(mgrsdigitBase)*xQty + float64(ed)
		yQty = float64(mgrsdigitBase)*yQty + float64(nd)
	}
	if centerCell {
		scale *= 2
		xQty = 2*xQty + 1
		yQty = 2*yQty + 1
	}
	easting = mgrsTileSize * xQty / scale
	northing = mgrsTileSize * yQty / scale
	return easting, northing, pairs, nil
}
