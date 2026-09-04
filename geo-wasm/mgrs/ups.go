package mgrs

import "math"

// WGS84 UPS polar stereographic (NGA / GeographicLib UPS k0).
func upsConformalFactor() float64 {
	e := math.Sqrt(wgsE2)
	return (1.0 - wgsF) * math.Exp(e*math.Atanh(e))
}

func polarStereographicRho(latAbsRad float64) float64 {
	if latAbsRad >= math.Pi/2-1e-15 {
		return 0
	}
	e := math.Sqrt(wgsE2)
	sinLat := math.Sin(latAbsRad)
	t := math.Tan(math.Pi/4-latAbsRad/2) /
		math.Pow((1-e*sinLat)/(1+e*sinLat), e/2)
	c := upsConformalFactor()
	return 2 * upsScaleK0 * WGSSemiMajorAxis * t / c
}

func forwardUPS(latDeg, lonDeg float64, north bool) (easting, northing float64) {
	lat := latDeg
	if !north {
		lat = -latDeg
	}
	latRad := lat * degRad
	if latRad > math.Pi/2 {
		latRad = math.Pi / 2
	}
	if latRad < 0 {
		latRad = 0
	}
	rho := polarStereographicRho(latRad)
	lonRad := lonDeg * degRad
	sinLon, cosLon := math.Sincos(lonRad)
	easting = upsFalseEast + rho*sinLon
	if north {
		northing = upsFalseNorth - rho*cosLon
	} else {
		northing = upsFalseNorth + rho*cosLon
	}
	return easting, northing
}

func inverseUPS(easting, northing float64, north bool) (latDeg, lonDeg float64) {
	dx := easting - upsFalseEast
	var dy float64
	if north {
		dy = upsFalseNorth - northing
	} else {
		dy = northing - upsFalseNorth
	}
	rho := math.Hypot(dx, dy)
	if rho < 1e-12 {
		if north {
			return 90, 0
		}
		return -90, 0
	}
	c := upsConformalFactor()
	t := rho * c / (2 * upsScaleK0 * WGSSemiMajorAxis)
	e := math.Sqrt(wgsE2)
	latRad := math.Pi/2 - 2*math.Atan(t)
	for range 10 {
		sinLat := math.Sin(latRad)
		latRad = math.Pi/2 - 2*math.Atan(t*math.Pow((1-e*sinLat)/(1+e*sinLat), e/2))
	}
	lonDeg = math.Atan2(dx, dy) * radDeg
	if north {
		latDeg = latRad * radDeg
	} else {
		latDeg = -latRad * radDeg
	}
	lonDeg -= 360 * math.Round(lonDeg/360)
	return latDeg, lonDeg
}
