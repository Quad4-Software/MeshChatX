package mgrs

import "math"

const degRad = math.Pi / 180

const radDeg = 180.0 / math.Pi

func meridianRadiusSin(sinPhi float64) float64 {
	ss := sinPhi * sinPhi
	return WGSSemiMajorAxis * (1.0 - wgsE2) / math.Pow(1.0-wgsE2*ss, 1.5)
}

func footpointLatitudeFromMeridionalDistance(m float64) float64 {
	phi := m / WGSSemiMajorAxis
	const epsFoot = 1e-14
	for range 16 {
		sinPhi := math.Sin(phi)
		f := wgsM(phi) - m
		if math.Abs(f) < epsFoot {
			break
		}
		phi -= f / meridianRadiusSin(sinPhi)
	}
	return phi
}

func normalizeLonDeltaRad(dlam float64) float64 {
	const twoPi = 2 * math.Pi
	for dlam > math.Pi {
		dlam -= twoPi
	}
	for dlam < -math.Pi {
		dlam += twoPi
	}
	return dlam
}

func longitudeZoneStandard(latDeg, lonDeg float64) int {
	if latDeg < -80 || latDeg >= 84 {
		return 0
	}
	ilon := int(math.Floor(lonDeg))
	if ilon >= 180 {
		ilon -= 360
	} else if ilon < -180 {
		ilon += 360
	}
	z := (ilon + 186) / 6
	b := latitudeBand(latDeg)
	switch {
	case b == 7 && z == 31 && ilon >= 3:
		return 32
	case b == 9 && ilon >= 0 && ilon < 42:
		return 2*((ilon+183)/12) + 1
	default:
		return z
	}
}

func latitudeBand(latDeg float64) int {
	ilat := int(math.Floor(latDeg))
	b := (ilat+80)/8 - 10
	if b < -10 {
		return -10
	}
	if b > 9 {
		return 9
	}
	return b
}

func forwardTM(latDeg, lonDeg float64, zone int, south bool) (e, n float64) {
	phi := latDeg * degRad
	lam := lonDeg * degRad
	lam0 := zoneCentralMeridianDeg(zone) * degRad
	dlam := normalizeLonDeltaRad(lam - lam0)

	sinPhi, cosPhi := math.Sincos(phi)
	tanPhi := sinPhi / cosPhi

	N := wgsNFromSin(sinPhi)
	T := tanPhi * tanPhi
	C := wgsEp2 * cosPhi * cosPhi
	A := dlam * cosPhi
	M := wgsM(phi)

	A2 := A * A
	A3 := A2 * A
	A4 := A3 * A
	A5 := A4 * A

	x := tmUTMScaleK0 * N * (A +
		(1.0-T+C)*A3/6.0 +
		(5.0-18.0*T+T*T+72.0*C-58.0*wgsEp2)*A5/120.0)
	y := tmUTMScaleK0 * (M + N*tanPhi*(A2/2.0+
		(5.0-T+9.0*C+4.0*C*C)*A4/24.0+
		(61.0-58.0*T+T*T+600.0*C-330.0*wgsEp2)*A2*A3/720.0))

	e = utmFalseEastM + x
	if south {
		n = utmSouthernFalseNorthM + y
	} else {
		n = y
	}
	return e, n
}

func inverseTM(e, n float64, zone int, south bool) (latDeg, lonDeg float64) {
	x := e - utmFalseEastM
	y := n
	if south {
		y -= utmSouthernFalseNorthM
	}

	M := y / tmUTMScaleK0
	phi1 := footpointLatitudeFromMeridionalDistance(M)

	sin1, cos1 := math.Sincos(phi1)
	tan1 := sin1 / cos1

	rho1 := meridianRadiusSin(sin1)
	nu1 := wgsNFromSin(sin1)
	T1 := tan1 * tan1
	C1 := wgsEp2 * cos1 * cos1

	D := x / (nu1 * tmUTMScaleK0)
	D2 := D * D
	D3 := D2 * D
	D4 := D3 * D
	D5 := D4 * D
	D6 := D5 * D

	phi := phi1 - nu1*tan1/rho1*(D2/2.0-
		(5.0+3.0*T1+10.0*C1-4.0*C1*C1-9.0*wgsEp2)*D4/24.0+
		(61.0+90.0*T1+298.0*C1+45.0*T1*T1-252.0*wgsEp2-3.0*C1*C1)*D6/720.0)

	lam := (D - (1.0+2.0*T1+C1)*D3/6.0 +
		(5.0-2.0*C1+28.0*T1-3.0*C1*C1+8.0*wgsEp2+24.0*T1*T1)*D5/120.0) / cos1

	lam0 := zoneCentralMeridianDeg(zone) * degRad
	lonRad := lam0 + lam
	lonDeg = lonRad * radDeg
	lonDeg -= 360 * math.Round(lonDeg/360)
	latDeg = phi * radDeg
	return latDeg, lonDeg
}
