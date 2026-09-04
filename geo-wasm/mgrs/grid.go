package mgrs

import "math"

func posMod(a, b int) int {
	r := a % b
	if r < 0 {
		r += b
	}
	return r
}

func utmRow(iband, icol, rowPeriodic int) int {
	const quad90 = 90.0

	c := 100.0 * float64(8*iband+4) / quad90
	hemiExtra := 0.0
	if iband >= 0 {
		hemiExtra = 0.1
	}

	minRow := -90
	if iband > -10 {
		minRow = int(math.Floor(c - 4.3 - hemiExtra))
	}
	maxRow := 94
	if iband < 9 {
		maxRow = int(math.Floor(c + 4.4 - hemiExtra))
	}
	baseRow := (minRow+maxRow)/2 - utmerowPeriod/2

	i := posMod(rowPeriodic-baseRow+maxUTMsRowTiles, utmerowPeriod) + baseRow
	if i < minRow || i > maxRow {
		sBand := iband
		if iband < 0 {
			sBand = -iband - 1
		}
		sRow := i
		if i < 0 {
			sRow = -i - 1
		}
		sCol := icol
		if icol >= 4 {
			sCol = -icol + 7
		}
		ok := (sRow == 70 && sBand == 8 && sCol >= 2) ||
			(sRow == 71 && sBand == 7 && sCol <= 2) ||
			(sRow == 79 && sBand == 9 && sCol >= 1) ||
			(sRow == 80 && sBand == 8 && sCol <= 1)
		if !ok {
			return maxUTMsRowTiles
		}
	}
	return i
}
