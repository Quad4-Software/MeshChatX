package mgrs

import "errors"

var (
	ErrLatOutOfUTMRange      = errors.New("mgrs: latitude outside [-80°, 84°) UTM MGRS belt")
	ErrInvalidDigitPairs     = errors.New("mgrs: invalid digit pair count")
	ErrShortBuffer           = errors.New("mgrs: destination buffer too small")
	ErrInvalidMGRS           = errors.New("mgrs: invalid MGRS string")
	ErrInvalidGrid           = errors.New("mgrs: easting/northing outside allowed UTM/UPS MGRS range")
	ErrLatitudeCoordsClash   = errors.New("mgrs: latitude band inconsistent with decoded northing metres")
	ErrInvalidGridSquareBand = errors.New("mgrs: 100km square not valid for latitude band")
)
