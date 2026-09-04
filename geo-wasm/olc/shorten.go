package olc

import (
	"fmt"
	"math"
)

// MinTrimmableCodeLen is the minimum full-code length that can be shortened.
const MinTrimmableCodeLen = 6

var pairResolutions = [...]float64{20.0, 1.0, 0.05, 0.0025, 0.000125}

// Shorten removes leading characters from a full Open Location Code using a reference location.
func Shorten(code string, lat, lng float64) (string, error) {
	if err := CheckFull(code); err != nil {
		return code, err
	}
	for i := 0; i < len(code); i++ {
		if code[i] == Padding {
			return code, ErrPadded
		}
	}

	var upperBuf [MaxEncodedLen]byte
	n := copyUpper(upperBuf[:], code)
	area, err := Decode(string(upperBuf[:n]))
	if err != nil {
		return code, err
	}
	if area.Len < MinTrimmableCodeLen {
		return code, fmt.Errorf("%w: need at least %d", ErrTooShort, MinTrimmableCodeLen)
	}

	lat, lng = clipLatitude(lat), normalizeLng(lng)
	centerLat, centerLng := area.Center()
	distance := math.Max(math.Abs(centerLat-lat), math.Abs(centerLng-lng))

	for i := len(pairResolutions) - 2; i >= 1; i-- {
		if distance < pairResolutions[i]*0.3 {
			return string(upperBuf[(i+1)*2 : n]), nil
		}
	}
	return string(upperBuf[:n]), nil
}

// RecoverNearest recovers the nearest full Open Location Code from a short code and reference point.
func RecoverNearest(code string, lat, lng float64) (string, error) {
	if err := CheckFull(code); err == nil {
		var buf [MaxEncodedLen]byte
		n := copyUpper(buf[:], code)
		return string(buf[:n]), nil
	}
	if err := CheckShort(code); err != nil {
		return code, ErrNotShort
	}

	lat, lng = clipLatitude(lat), normalizeLng(lng)

	sep := -1
	for i := 0; i < len(code); i++ {
		if code[i] == Separator {
			sep = i
			break
		}
	}
	padLen := sepPos - sep
	resolution := math.Pow(20, float64(2-(padLen/2)))
	halfRes := resolution / 2

	var merged [MaxEncodedLen]byte
	if _, err := EncodeTo(merged[:], lat, lng, 0); err != nil {
		return code, err
	}
	write := padLen
	for i := 0; i < len(code); i++ {
		merged[write] = upper(code[i])
		write++
	}
	area, err := Decode(string(merged[:write]))
	if err != nil {
		return code, err
	}

	centerLat, centerLng := area.Center()
	if lat+halfRes < centerLat && centerLat-resolution >= -latMax {
		centerLat -= resolution
	} else if lat-halfRes > centerLat && centerLat+resolution <= latMax {
		centerLat += resolution
	}
	if lng+halfRes < centerLng {
		centerLng -= resolution
	} else if lng-halfRes > centerLng {
		centerLng += resolution
	}

	return Encode(centerLat, centerLng, area.Len), nil
}

func copyUpper(dst []byte, code string) int {
	n := min(len(code), len(dst))
	for i := range n {
		dst[i] = upper(code[i])
	}
	return n
}
