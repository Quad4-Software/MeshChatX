package olc

import "errors"

// Decode decodes a full Open Location Code into its CodeArea.
// Only the first 15 significant digits are used.
func Decode(code string) (CodeArea, error) {
	var area CodeArea
	if err := CheckFull(code); err != nil {
		return area, err
	}
	var digits [maxCodeLen]byte
	codeLen := stripInto(digits[:], code)
	if codeLen < 2 {
		return area, errors.New("olc: code too short")
	}
	return decodeDigits(digits[:codeLen]), nil
}

func stripInto(dst []byte, code string) int {
	n := 0
	for i := 0; i < len(code) && n < len(dst); i++ {
		r := code[i]
		if r == Separator || r == Padding {
			continue
		}
		dst[n] = upper(r)
		n++
	}
	return n
}

func decodeDigits(code []byte) CodeArea {
	codeLen := len(code)
	var lat, lng int64
	var height int64 = 1
	var width int64

	for i := 0; i < pairCodeLen; i += 2 {
		lat *= encBase
		lng *= encBase
		height *= encBase
		if i+1 < codeLen {
			lat += int64(alphabetIndex(code[i]))
			lng += int64(alphabetIndex(code[i+1]))
			height = 1
		}
	}
	width = height

	for i := pairCodeLen; i < maxCodeLen; i++ {
		lat *= gridRows
		height *= gridRows
		lng *= gridCols
		width *= gridCols
		if i < codeLen {
			dval := int64(alphabetIndex(code[i]))
			lat += dval / gridCols
			lng += dval % gridCols
			height = 1
			width = 1
		}
	}

	latDegrees := float64(lat-latOffset) / float64(finalLatPrecision)
	lngDegrees := float64(lng-lngOffset) / float64(finalLngPrecision)
	heightDegrees := float64(height) / float64(finalLatPrecision)
	widthDegrees := float64(width) / float64(finalLngPrecision)

	return CodeArea{
		LatLo: latDegrees,
		LngLo: lngDegrees,
		LatHi: latDegrees + heightDegrees,
		LngHi: lngDegrees + widthDegrees,
		Len:   codeLen,
	}
}
