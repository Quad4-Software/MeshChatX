package mgrs

import "math"

const degRad = math.Pi / 180

const radDeg = 180.0 / math.Pi

var (
	wgsThirdFlattening = wgsF / (2.0 - wgsF)
	tmN2               = wgsThirdFlattening * wgsThirdFlattening
	tmN3               = tmN2 * wgsThirdFlattening
	tmN4               = tmN3 * wgsThirdFlattening
	tmN5               = tmN4 * wgsThirdFlattening
	tmN6               = tmN5 * wgsThirdFlattening
	tmRectifyingRadius = WGSSemiMajorAxis / (1.0 + wgsThirdFlattening) *
		(1.0 + tmN2/4.0 + tmN4/64.0 + tmN6/256.0)

	tmAlpha = [...]float64{
		0.5*wgsThirdFlattening - 2.0/3.0*tmN2 + 5.0/16.0*tmN3 + 41.0/180.0*tmN4 - 127.0/288.0*tmN5 + 7891.0/37800.0*tmN6,
		13.0/48.0*tmN2 - 3.0/5.0*tmN3 + 557.0/1440.0*tmN4 + 281.0/630.0*tmN5 - 1983433.0/1935360.0*tmN6,
		61.0/240.0*tmN3 - 103.0/140.0*tmN4 + 15061.0/26880.0*tmN5 + 167603.0/181440.0*tmN6,
		49561.0/161280.0*tmN4 - 179.0/168.0*tmN5 + 6601661.0/7257600.0*tmN6,
		34729.0/80640.0*tmN5 - 3418889.0/1995840.0*tmN6,
		212378941.0 / 319334400.0 * tmN6,
	}
	tmBeta = [...]float64{
		0.5*wgsThirdFlattening - 2.0/3.0*tmN2 + 37.0/96.0*tmN3 - 1.0/360.0*tmN4 - 81.0/512.0*tmN5 + 96199.0/604800.0*tmN6,
		1.0/48.0*tmN2 + 1.0/15.0*tmN3 - 437.0/1440.0*tmN4 + 46.0/105.0*tmN5 - 1118711.0/3870720.0*tmN6,
		17.0/480.0*tmN3 - 37.0/840.0*tmN4 - 209.0/4480.0*tmN5 + 5569.0/90720.0*tmN6,
		4397.0/161280.0*tmN4 - 11.0/504.0*tmN5 - 830251.0/7257600.0*tmN6,
		4583.0/161280.0*tmN5 - 108847.0/3991680.0*tmN6,
		20648693.0 / 638668800.0 * tmN6,
	}
	tmDelta = [...]float64{
		2.0*wgsThirdFlattening - 2.0/3.0*tmN2 - 2.0*tmN3 + 116.0/45.0*tmN4 + 26.0/45.0*tmN5 - 2854.0/675.0*tmN6,
		7.0/3.0*tmN2 - 8.0/5.0*tmN3 - 227.0/45.0*tmN4 + 2704.0/315.0*tmN5 + 2323.0/945.0*tmN6,
		56.0/15.0*tmN3 - 136.0/35.0*tmN4 - 1262.0/105.0*tmN5 + 73814.0/2835.0*tmN6,
		4279.0/630.0*tmN4 - 332.0/35.0*tmN5 - 399572.0/14175.0*tmN6,
		4174.0/315.0*tmN5 - 144838.0/6237.0*tmN6,
		601676.0 / 22275.0 * tmN6,
	}
)

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

func normalizeLongitudeDeg(lonDeg float64) float64 {
	lon := math.Mod(lonDeg+180, 360)
	if lon < 0 {
		lon += 360
	}
	return lon - 180
}

func longitudeZoneStandard(latDeg, lonDeg float64) int {
	if latDeg < -80 || latDeg >= 84 {
		return 0
	}
	ilon := int(math.Floor(normalizeLongitudeDeg(lonDeg)))
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

	sinPhi := math.Sin(phi)
	sinLam, cosLam := math.Sincos(dlam)
	ecc := math.Sqrt(wgsE2)
	taup := math.Sinh(math.Atanh(sinPhi) - ecc*math.Atanh(ecc*sinPhi))

	xiPrime := math.Atan2(taup, cosLam)
	etaPrime := math.Asinh(sinLam / math.Hypot(taup, cosLam))
	xi := xiPrime
	eta := etaPrime
	for j := 1; j <= len(tmAlpha); j++ {
		a := 2 * float64(j)
		xi += tmAlpha[j-1] * math.Sin(a*xiPrime) * math.Cosh(a*etaPrime)
		eta += tmAlpha[j-1] * math.Cos(a*xiPrime) * math.Sinh(a*etaPrime)
	}

	e = utmFalseEastM + tmUTMScaleK0*tmRectifyingRadius*eta
	n = tmUTMScaleK0 * tmRectifyingRadius * xi
	if south {
		n += utmSouthernFalseNorthM
	}
	return e, n
}

func inverseTM(e, n float64, zone int, south bool) (latDeg, lonDeg float64) {
	y := n
	if south {
		y -= utmSouthernFalseNorthM
	}
	xi := y / (tmUTMScaleK0 * tmRectifyingRadius)
	eta := (e - utmFalseEastM) / (tmUTMScaleK0 * tmRectifyingRadius)

	xiPrime := xi
	etaPrime := eta
	for j := 1; j <= len(tmBeta); j++ {
		a := 2 * float64(j)
		xiPrime -= tmBeta[j-1] * math.Sin(a*xi) * math.Cosh(a*eta)
		etaPrime -= tmBeta[j-1] * math.Cos(a*xi) * math.Sinh(a*eta)
	}

	sinChi := math.Sin(xiPrime) / math.Cosh(etaPrime)
	sinChi = math.Max(-1, math.Min(1, sinChi))
	chi := math.Asin(sinChi)
	phi := chi
	for j := 1; j <= len(tmDelta); j++ {
		phi += tmDelta[j-1] * math.Sin(2*float64(j)*chi)
	}
	lonDelta := math.Atan2(math.Sinh(etaPrime), math.Cos(xiPrime))

	lonDeg = zoneCentralMeridianDeg(zone) + lonDelta*radDeg
	lonDeg -= 360 * math.Round(lonDeg/360)
	latDeg = phi * radDeg
	return latDeg, lonDeg
}
