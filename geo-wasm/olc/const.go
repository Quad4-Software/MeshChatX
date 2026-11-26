package olc

import "math"

const (
	encBase     = 20
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
)

const (
	// Separator is the character that separates the leading and trailing code sections.
	Separator = '+'
	// Padding is the character used to pad codes with fewer than eight significant digits.
	Padding = '0'
	// Alphabet is the ordered set of Open Location Code digits.
	Alphabet = "23456789CFGHJMPQRVWX"

	// DefaultCodeLen is the number of significant digits produced when codeLen is zero or negative.
	DefaultCodeLen = 10
	// MaxCodeLen is the maximum number of significant digits in an encoded code.
	MaxCodeLen = 15
	// MaxEncodedLen is the maximum byte length produced by Encode, including the separator.
	MaxEncodedLen = MaxCodeLen + 1
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

// CodeArea is the geographic area represented by an Open Location Code.
type CodeArea struct {
	// LatLo and LngLo are the south and west bounds.
	LatLo, LngLo float64
	// LatHi and LngHi are the north and east bounds.
	LatHi, LngHi float64
	// Len is the number of significant digits in the decoded code.
	Len int
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
	if math.IsNaN(lat) {
		return 0
	}
	if lat > latMax {
		return latMax
	}
	if lat < -latMax {
		return -latMax
	}
	return lat
}

// normalizeLng wraps value into [-180, 180). Non-finite input returns 0.
func normalizeLng(value float64) float64 {
	if math.IsNaN(value) || math.IsInf(value, 0) {
		return 0
	}
	value = math.Mod(value, 2*lngMax)
	if value >= lngMax {
		return value - 2*lngMax
	}
	if value < -lngMax {
		return value + 2*lngMax
	}
	return value
}

// longitudeDelta returns a-b wrapped into [-180, 180). Inputs must already be normalized.
func longitudeDelta(a, b float64) float64 {
	diff := a - b
	if diff >= lngMax {
		return diff - 2*lngMax
	}
	if diff < -lngMax {
		return diff + 2*lngMax
	}
	return diff
}

// floorMul returns floor(degrees * precision), snapping values within two
// floating-point steps of an integer. That corrects products that land just
// below an exact multiple (for example 40.6 * precision) without moving values
// more than two steps below the boundary.
func floorMul(degrees, precision float64) int64 {
	x := degrees * precision
	nearest := math.Round(x)
	diff := x - nearest
	if diff < 0 {
		diff = -diff
	}
	absX := math.Abs(x)
	ulp := math.Nextafter(absX, math.Inf(1)) - absX
	if diff <= 2*ulp {
		return int64(nearest)
	}
	return int64(math.Floor(x))
}

func latitudeAsInteger(latDegrees float64) int64 {
	latVal := floorMul(clipLatitude(latDegrees), finalLatPrecision) + latOffset
	if latVal < 0 {
		return 0
	}
	if latVal >= latRange {
		return latRange - 1
	}
	return latVal
}

func longitudeAsInteger(lngDegrees float64) int64 {
	lngVal := floorMul(normalizeLng(lngDegrees), finalLngPrecision) + lngOffset
	if lngVal < 0 {
		return (lngVal%lngMod + lngMod) % lngMod
	}
	if lngVal >= lngMod {
		return lngVal % lngMod
	}
	return lngVal
}

func alphabetIndex(b byte) int {
	return int(alphabetIndexTable[b])
}

// EncodedLen returns the byte length of an encoded code for codeLen, including the separator.
// It is the minimum destination length required by EncodeTo.
func EncodedLen(codeLen int) int {
	codeLen = clipCodeLen(codeLen)
	if codeLen >= sepPos {
		return codeLen + 1
	}
	return sepPos + 1
}
