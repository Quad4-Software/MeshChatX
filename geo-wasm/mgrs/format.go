package mgrs

import "strings"

// FormatSpaced returns a canonical spaced MGRS string (GZD square easting
// northing). Input may be compact or already spaced, and one-digit UTM zones
// are zero-padded. DigitPairs 0 omits numeric groups.
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
	if p.Zone != ZoneUPS {
		b.WriteByte(digits[p.Zone/mgrsdigitBase])
		b.WriteByte(digits[p.Zone%mgrsdigitBase])
	}
	b.WriteByte(p.Band)
	if p.DigitPairs < 0 {
		return b.String(), nil
	}
	b.WriteByte(' ')
	b.WriteByte(p.Col)
	b.WriteByte(p.Row)
	if p.DigitPairs > 0 {
		tail := data[len(data)-2*p.DigitPairs:]
		half := len(tail) / 2
		b.WriteByte(' ')
		b.Write(tail[:half])
		b.WriteByte(' ')
		b.Write(tail[half:])
	}
	return b.String(), nil
}
