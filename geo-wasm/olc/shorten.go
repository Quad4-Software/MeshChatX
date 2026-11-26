package olc

import (
	"fmt"
	"math"
	"strings"
)

// MinTrimmableCodeLen is the minimum full-code length that can be shortened.
const MinTrimmableCodeLen = 6

// missingPairResolutions maps padLen/2 values 1 through 4 to the degree
// resolution of the missing leading pairs.
var missingPairResolutions = [...]float64{20, 1, 0.05, 0.0025}

// trimSteps is ordered from smallest to largest resolution. start is the byte
// index of the first retained character.
var trimSteps = [...]struct {
	resolution float64
	start      int
}{
	{0.0025, 8},
	{0.05, 6},
	{1.0, 4},
}

// Shorten removes leading characters from a full Open Location Code using a reference location.
// If the reference is not close enough, it returns the uppercased full code.
// On error, it returns code unchanged. Reference coordinates use the same clipping
// and normalization rules as Encode. Longitude distance is circular, so references
// on opposite sides of the antimeridian can still be close.
func Shorten(code string, lat, lng float64) (string, error) {
	dst, err := AppendShorten(nil, code, lat, lng)
	if err != nil {
		return code, err
	}
	return string(dst), nil
}

// AppendShorten appends the shortened form of a full Open Location Code to dst
// using a reference location. On error, dst is returned unchanged. It is the
// zero-allocation variant of Shorten when the caller reuses a buffer.
func AppendShorten(dst []byte, code string, lat, lng float64) ([]byte, error) {
	if err := CheckFull(code); err != nil {
		return dst, err
	}
	if strings.IndexByte(code, Padding) >= 0 {
		return dst, ErrPadded
	}

	var upperBuf [MaxEncodedLen]byte
	n := copyUpper(upperBuf[:], code)

	var digits [MaxCodeLen]byte
	area := decodeDigits(digits[:stripInto(digits[:], code)])
	if area.Len < MinTrimmableCodeLen {
		return dst, fmt.Errorf("%w: need at least %d", ErrTooShort, MinTrimmableCodeLen)
	}

	lat, lng = clipLatitude(lat), normalizeLng(lng)
	centerLat, centerLng := area.Center()
	distance := math.Max(math.Abs(centerLat-lat), math.Abs(longitudeDelta(centerLng, lng)))

	start := 0
	for _, step := range trimSteps {
		if distance < step.resolution*0.3 {
			start = step.start
			break
		}
	}
	if len(code) <= MaxEncodedLen {
		return append(dst, upperBuf[start:n]...), nil
	}
	dst = append(dst, upperBuf[start:n]...)
	for i := n; i < len(code); i++ {
		dst = append(dst, upper(code[i]))
	}
	return dst, nil
}

// RecoverNearest recovers the nearest full Open Location Code from a short code and reference point.
// A valid full code is returned uppercased and otherwise unchanged. On error,
// it returns code unchanged. Reference coordinates use the same clipping and
// normalization rules as Encode. Longitude distance is circular, so recovery
// works across the antimeridian.
func RecoverNearest(code string, lat, lng float64) (string, error) {
	dst, err := AppendRecoverNearest(nil, code, lat, lng)
	if err != nil {
		return code, err
	}
	return string(dst), nil
}

// AppendRecoverNearest appends the nearest full Open Location Code for a short
// code and reference point to dst. A valid full code is appended uppercased and
// otherwise unchanged. On error, dst is returned unchanged. It is the
// zero-allocation variant of RecoverNearest when the caller reuses a buffer.
func AppendRecoverNearest(dst []byte, code string, lat, lng float64) ([]byte, error) {
	if err := CheckFull(code); err == nil {
		for i := 0; i < len(code); i++ {
			dst = append(dst, upper(code[i]))
		}
		return dst, nil
	}
	if err := CheckShort(code); err != nil {
		return dst, err
	}

	lat, lng = clipLatitude(lat), normalizeLng(lng)

	sep := strings.IndexByte(code, Separator)
	padLen := sepPos - sep
	resolution := missingPairResolutions[padLen/2-1]
	halfRes := resolution / 2

	var merged [MaxEncodedLen]byte
	integerEncodeTo(merged[:], latitudeAsInteger(lat), longitudeAsInteger(lng), 0)
	write := padLen
	for i := 0; i < len(code) && write < len(merged); i++ {
		merged[write] = upper(code[i])
		write++
	}

	var digits [MaxCodeLen]byte
	dlen := 0
	for i := 0; i < write; i++ {
		b := merged[i]
		if b == Separator || b == Padding {
			continue
		}
		digits[dlen] = b
		dlen++
	}
	area := decodeDigits(digits[:dlen])

	centerLat, centerLng := area.Center()
	if lat+halfRes < centerLat && centerLat-resolution >= -latMax {
		centerLat -= resolution
	} else if lat-halfRes > centerLat && centerLat+resolution <= latMax {
		centerLat += resolution
	}
	if delta := longitudeDelta(centerLng, lng); delta > halfRes {
		centerLng -= resolution
	} else if delta < -halfRes {
		centerLng += resolution
	}

	var buf [MaxEncodedLen]byte
	n := integerEncodeTo(buf[:], latitudeAsInteger(centerLat), longitudeAsInteger(centerLng), area.Len)
	return append(dst, buf[:n]...), nil
}

func copyUpper(dst []byte, code string) int {
	n := min(len(code), len(dst))
	for i := range n {
		dst[i] = upper(code[i])
	}
	return n
}
