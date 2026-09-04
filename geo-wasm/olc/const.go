package olc

import "math"

const (
	Separator = '+'
	Padding   = '0'
	Alphabet  = "23456789CFGHJMPQRVWX"

	encBase     = 20
	maxCodeLen  = 15
	pairCodeLen = 10
	gridCols    = 4
	gridRows    = 5
	sepPos      = 8

	pairPrecision    = 8000
	gridLatFullValue = 3125 // 5**5
	gridLngFullValue = 1024 // 4**5

	finalLatPrecision = pairPrecision * gridLatFullValue
	finalLngPrecision = pairPrecision * gridLngFullValue

	latMax = 90
	lngMax = 180

	latOffset = latMax * finalLatPrecision
	lngOffset = lngMax * finalLngPrecision
	latRange  = 2 * latMax * finalLatPrecision
	lngMod    = 2 * lngMax * finalLngPrecision

	// MaxEncodedLen is the maximum byte length of a Open Location Code including '+'.
	MaxEncodedLen = maxCodeLen + 1
)

var alphabetIndexTable [256]int8

func init() {
	for i := range alphabetIndexTable {
		alphabetIndexTable[i] = -1
	}
	for i := range len(Alphabet) {
		c := Alphabet[i]
		alphabetIndexTable[c] = int8(i)
		if c >= 'A' && c <= 'Z' {
			alphabetIndexTable[c-'A'+'a'] = int8(i)
		}
	}
}

// CodeArea is the geographic area represented by a Open Location Code.
type CodeArea struct {
	LatLo, LngLo, LatHi, LngHi float64
	Len                        int
}

// Center returns the latitude and longitude of the area center.
func (a CodeArea) Center() (lat, lng float64) {
	return math.Min(a.LatLo+(a.LatHi-a.LatLo)/2, latMax),
		math.Min(a.LngLo+(a.LngHi-a.LngLo)/2, lngMax)
}

func upper(b byte) byte {
	if b >= 'a' && b <= 'z' {
		return b - ('a' - 'A')
	}
	return b
}

func clipLatitude(lat float64) float64 {
	if lat > latMax {
		return latMax
	}
	if lat < -latMax {
		return -latMax
	}
	return lat
}

func normalizeLng(value float64) float64 {
	for value < -lngMax {
		value += 2 * lngMax
	}
	for value >= lngMax {
		value -= 2 * lngMax
	}
	return value
}

// floorMul returns floor(degrees * precision), snapping values that are within
// a tiny relative epsilon of an integer. That corrects float64 products that
// land just below an exact multiple (for example 40.6 * precision).
func floorMul(degrees, precision float64) int64 {
	x := degrees * precision
	nearest := math.Round(x)
	diff := x - nearest
	if diff < 0 {
		diff = -diff
	}
	limit := nearest
	if limit < 0 {
		limit = -limit
	}
	if limit < 1 {
		limit = 1
	}
	if diff <= limit*1e-15 {
		return int64(nearest)
	}
	return int64(math.Floor(x))
}

func latitudeAsInteger(latDegrees float64) int64 {
	latVal := floorMul(latDegrees, finalLatPrecision) + latOffset
	if latVal < 0 {
		return 0
	}
	if latVal >= latRange {
		return latRange - 1
	}
	return latVal
}

func longitudeAsInteger(lngDegrees float64) int64 {
	lngVal := floorMul(lngDegrees, finalLngPrecision) + lngOffset
	if lngVal < 0 {
		return lngVal%lngMod + lngMod
	}
	if lngVal >= lngMod {
		return lngVal % lngMod
	}
	return lngVal
}

func alphabetIndex(b byte) int {
	return int(alphabetIndexTable[b])
}

// EncodedLen returns the byte length of an encoded code for codeLen, including '+'.
// EncodeTo still requires a destination of MaxEncodedLen because encoding uses a
// fixed workspace before truncating to this length.
func EncodedLen(codeLen int) int {
	codeLen = clipCodeLen(codeLen)
	if codeLen >= sepPos {
		return codeLen + 1
	}
	return sepPos + 1
}
