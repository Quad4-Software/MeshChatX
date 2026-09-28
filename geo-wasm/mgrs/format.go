package mgrs

import "strings"

// FormatSpaced returns a spaced MGRS string (GZD square easting northing).
// Input may be compact or already spaced. DigitPairs 0 omits numeric groups.
func FormatSpaced(compactOrSpaced string) (string, error) {
	data := compactUpperASCIIFromString(compactOrSpaced)
	if len(data) == 0 {
		return "", ErrInvalidMGRS
	}
	p, err := decodeNormalizedParts(data, false)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	// GZD width is the zone digits plus the band. Single-digit UTM zones
	// (1-9) encode one digit, UPS encodes no zone at all.
	zoneDigits := 0
	if p.Zone != ZoneUPS {
		if p.Zone >= 1 && p.Zone <= 9 {
			zoneDigits = 1
		} else {
			zoneDigits = 2
		}
	}
	gzdLen := zoneDigits + 1
	prefix := gzdLen + 2
	if len(data) < prefix {
		return "", ErrInvalidMGRS
	}
	b.Write(data[:gzdLen])
	b.WriteByte(' ')
	b.WriteByte(p.Col)
	b.WriteByte(p.Row)
	if p.DigitPairs > 0 {
		tail := data[prefix:]
		half := len(tail) / 2
		b.WriteByte(' ')
		b.Write(tail[:half])
		b.WriteByte(' ')
		b.Write(tail[half:])
	}
	return b.String(), nil
}
