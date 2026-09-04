package olc

import "errors"

// ErrShortBuffer means dst was too small for EncodeTo.
var ErrShortBuffer = errors.New("olc: short buffer")

// Encode converts latitude and longitude into a Open Location Code of the given length.
//
// lat is clipped to [-90, 90]. lng is normalised to [-180, 180).
// If codeLen <= 0, the default length of 10 is used. Odd lengths below 10 are
// rounded up to even. Lengths above 15 are clipped to 15.
func Encode(lat, lng float64, codeLen int) string {
	var buf [MaxEncodedLen]byte
	n := integerEncodeTo(buf[:], latitudeAsInteger(lat), longitudeAsInteger(lng), codeLen)
	return string(buf[:n])
}

// EncodeBytes is like Encode but returns ASCII bytes.
func EncodeBytes(lat, lng float64, codeLen int) []byte {
	var buf [MaxEncodedLen]byte
	n := integerEncodeTo(buf[:], latitudeAsInteger(lat), longitudeAsInteger(lng), codeLen)
	out := make([]byte, n)
	copy(out, buf[:n])
	return out
}

// EncodeTo writes a Open Location Code into dst and returns the number of bytes written.
// dst must have length >= MaxEncodedLen. This is the zero-allocation encode
// path when the caller reuses a buffer.
func EncodeTo(dst []byte, lat, lng float64, codeLen int) (int, error) {
	if len(dst) < MaxEncodedLen {
		return 0, ErrShortBuffer
	}
	return integerEncodeTo(dst, latitudeAsInteger(lat), longitudeAsInteger(lng), codeLen), nil
}

// AppendEncode appends an encoded Open Location Code to dst.
func AppendEncode(dst []byte, lat, lng float64, codeLen int) []byte {
	old := len(dst)
	if cap(dst)-old < MaxEncodedLen {
		newCap := max(old*2+MaxEncodedLen, old+MaxEncodedLen)
		out := make([]byte, old, newCap)
		copy(out, dst)
		dst = out
	}
	n := integerEncodeTo(dst[old:old+MaxEncodedLen], latitudeAsInteger(lat), longitudeAsInteger(lng), codeLen)
	return dst[:old+n]
}

func integerEncode(latVal, lngVal int64, codeLen int) string {
	var buf [MaxEncodedLen]byte
	n := integerEncodeTo(buf[:], latVal, lngVal, codeLen)
	return string(buf[:n])
}

func integerEncodeTo(dst []byte, latVal, lngVal int64, codeLen int) int {
	codeLen = clipCodeLen(codeLen)
	copy(dst, "00000000+0012345")

	if codeLen > pairCodeLen {
		for i := maxCodeLen - pairCodeLen; i >= 1; i-- {
			latDigit := latVal % int64(gridRows)
			lngDigit := lngVal % int64(gridCols)
			dst[sepPos+2+i] = Alphabet[latDigit*gridCols+lngDigit]
			latVal /= int64(gridRows)
			lngVal /= int64(gridCols)
		}
	} else {
		latVal /= gridLatFullValue
		lngVal /= gridLngFullValue
	}

	dst[sepPos+2], lngVal = pairIndexStep(lngVal)
	dst[sepPos+1], latVal = pairIndexStep(latVal)

	for pairStart := pairCodeLen/2 + 1; pairStart >= 0; pairStart -= 2 {
		dst[pairStart+1], lngVal = pairIndexStep(lngVal)
		dst[pairStart], latVal = pairIndexStep(latVal)
	}

	if codeLen >= sepPos {
		return codeLen + 1
	}
	for i := codeLen; i < sepPos; i++ {
		dst[i] = Padding
	}
	return sepPos + 1
}

func clipCodeLen(codeLen int) int {
	switch {
	case codeLen <= 0:
		return pairCodeLen
	case codeLen < pairCodeLen && codeLen%2 == 1:
		return codeLen + 1
	case codeLen > maxCodeLen:
		return maxCodeLen
	default:
		return codeLen
	}
}

func pairIndexStep(coordinate int64) (digit byte, remaining int64) {
	ndx := coordinate % encBase
	coordinate /= encBase
	return Alphabet[ndx], coordinate
}
