package mgrs

// WGS84 semi-major axis (m), NGA STND.0036.
const WGSSemiMajorAxis = 6378137.0

// WGS84 inverse flattening 1/f, NGA STND.0036.
const WGSInverseFlattening = 298.257223563

const tmUTMScaleK0 = 0.9996

var (
	wgsF  = 1.0 / WGSInverseFlattening
	wgsE2 = wgsF * (2.0 - wgsF)
)
