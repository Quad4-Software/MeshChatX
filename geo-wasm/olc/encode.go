package olc

import (
	"errors"
	"slices"
)

// ErrShortBuffer means dst was too small for EncodeTo.
var ErrShortBuffer = errors.New("olc: short buffer")

// Encode converts latitude and longitude into an Open Location Code of the given length.
//
// lat is clipped to [-90, 90]. lng is normalized to [-180, 180).
// Coordinates within two floating-point steps of a grid boundary are treated
// as exactly on the boundary to compensate for binary representation error.
// NaN coordinates encode as 0 degrees. Infinite latitudes clip to the poles
// and infinite longitudes encode as 0.
// If codeLen <= 0, DefaultCodeLen is used. Odd lengths below DefaultCodeLen are
// rounded up to even. Lengths above MaxCodeLen are clipped to MaxCodeLen.
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

// EncodeTo writes an Open Location Code into dst and returns the number of bytes written.
// dst must have length at least EncodedLen(codeLen). This is the zero-allocation
// encode path when the caller reuses a buffer.
func EncodeTo(dst []byte, lat, lng float64, codeLen int) (int, error) {
	need := EncodedLen(codeLen)
	if len(dst) < need {
		return 0, ErrShortBuffer
	}
	latVal, lngVal := latitudeAsInteger(lat), longitudeAsInteger(lng)
	if len(dst) >= MaxEncodedLen {
		return integerEncodeTo(dst, latVal, lngVal, codeLen), nil
	}
	var buf [MaxEncodedLen]byte
	n := integerEncodeTo(buf[:], latVal, lngVal, codeLen)
	return copy(dst, buf[:n]), nil
}

// AppendEncode appends an encoded Open Location Code to dst.
func AppendEncode(dst []byte, lat, lng float64, codeLen int) []byte {
	old := len(dst)
	dst = slices.Grow(dst, MaxEncodedLen)
	n := integerEncodeTo(dst[old:old+MaxEncodedLen], latitudeAsInteger(lat), longitudeAsInteger(lng), codeLen)
	return dst[:old+n]
}

// integerEncodeTo writes into dst, which must have length at least MaxEncodedLen.
func integerEncodeTo(dst []byte, latVal, lngVal int64, codeLen int) int {
	codeLen = clipCodeLen(codeLen)
	copy(dst, "00000000+0012345")

	if codeLen > pairCodeLen {
		for i := MaxCodeLen - pairCodeLen; i >= 1; i-- {
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
		return DefaultCodeLen
	case codeLen < pairCodeLen && codeLen%2 == 1:
		return codeLen + 1
	case codeLen > MaxCodeLen:
		return MaxCodeLen
	default:
		return codeLen
	}
}

func pairIndexStep(coordinate int64) (digit byte, remaining int64) {
	ndx := coordinate % encBase
	coordinate /= encBase
	return Alphabet[ndx], coordinate
}
