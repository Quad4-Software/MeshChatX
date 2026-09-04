package mgrs

import "math"

// WGS84 semi-major axis (m), NGA STND.0036.
const WGSSemiMajorAxis = 6378137.0

// WGS84 inverse flattening 1/f, NGA STND.0036.
const WGSInverseFlattening = 298.257223563

var (
	wgsF         = 1.0 / WGSInverseFlattening
	wgsE2        = wgsF * (2.0 - wgsF)
	wgsEp2       = wgsE2 / (1.0 - wgsE2)
	tmUTMScaleK0 = 0.9996
)

func wgsNFromSin(sinPhi float64) float64 {
	return WGSSemiMajorAxis / math.Sqrt(1.0-wgsE2*sinPhi*sinPhi)
}

func wgsM(phi float64) float64 {
	return WGSSemiMajorAxis * ((1.0-wgsE2/4.0-3.0*wgsE2*wgsE2/64.0-5.0*wgsE2*wgsE2*wgsE2/256.0)*phi -
		(3.0*wgsE2/8.0+3.0*wgsE2*wgsE2/32.0+45.0*wgsE2*wgsE2*wgsE2/1024.0)*math.Sin(2.0*phi) +
		(15.0*wgsE2*wgsE2/256.0+45.0*wgsE2*wgsE2*wgsE2/1024.0)*math.Sin(4.0*phi) -
		(35.0 * wgsE2 * wgsE2 * wgsE2 / 3072.0 * math.Sin(6.0*phi)))
}
