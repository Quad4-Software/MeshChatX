package olc

import (
	"errors"
	"fmt"
)

var (
	ErrEmpty    = errors.New("olc: empty code")
	ErrInvalid  = errors.New("olc: invalid code")
	ErrShort    = errors.New("olc: short code")
	ErrNotShort = errors.New("olc: not a short code")
	ErrPadded   = errors.New("olc: cannot shorten padded code")
	ErrTooShort = errors.New("olc: code too short to shorten")
)

// Check reports whether code is a valid Open Location Code sequence (full, padded, or short).
func Check(code string) error {
	if code == "" || (len(code) == 1 && code[0] == Separator) {
		return ErrEmpty
	}
	n := len(code)
	firstSep, firstPad := -1, -1
	for i := range n {
		r := code[i]
		if firstPad != -1 {
			switch r {
			case Padding:
				continue
			case Separator:
				if firstSep != -1 {
					return fmt.Errorf("%w: extraneous separator at %d", ErrInvalid, i)
				}
				firstSep = i
				if n-1 == i {
					continue
				}
			}
			return fmt.Errorf("%w: %q after padding at %d", ErrInvalid, r, i)
		}
		if alphabetIndex(r) >= 0 {
			continue
		}
		switch r {
		case Separator:
			if firstSep != -1 {
				return fmt.Errorf("%w: extra separator at %d", ErrInvalid, i)
			}
			if i > sepPos || i%2 == 1 {
				return fmt.Errorf("%w: separator in illegal position %d", ErrInvalid, i)
			}
			firstSep = i
		case Padding:
			if i == 0 {
				return fmt.Errorf("%w: starts with padding", ErrInvalid)
			}
			firstPad = i
		default:
			return fmt.Errorf("%w: invalid character %q at %d", ErrInvalid, r, i)
		}
	}
	if firstSep == -1 {
		return fmt.Errorf("%w: missing separator", ErrInvalid)
	}
	if n-firstSep-1 == 1 {
		return fmt.Errorf("%w: only one character after separator", ErrInvalid)
	}
	if firstPad != -1 {
		if firstSep < sepPos {
			return fmt.Errorf("%w: short codes cannot have padding", ErrInvalid)
		}
		if firstPad%2 == 1 {
			return fmt.Errorf("%w: odd number of padding characters", ErrInvalid)
		}
	}
	return nil
}

// CheckShort reports whether code is a valid short Open Location Code.
func CheckShort(code string) error {
	if err := Check(code); err != nil {
		return err
	}
	for i := 0; i < len(code); i++ {
		if code[i] == Separator {
			if i < sepPos {
				return nil
			}
			break
		}
	}
	return ErrNotShort
}

// CheckFull reports whether code is a valid full Open Location Code.
func CheckFull(code string) error {
	if err := CheckShort(code); err == nil {
		return ErrShort
	} else if !errors.Is(err, ErrNotShort) {
		return err
	}
	if alphabetIndex(code[0])*encBase >= latMax*2 {
		return fmt.Errorf("%w: latitude outside range", ErrInvalid)
	}
	if len(code) > 1 && alphabetIndex(code[1])*encBase >= lngMax*2 {
		return fmt.Errorf("%w: longitude outside range", ErrInvalid)
	}
	return nil
}

// IsValid reports whether code is a valid Open Location Code sequence.
func IsValid(code string) bool { return Check(code) == nil }

// IsShort reports whether code is a valid short Open Location Code.
func IsShort(code string) bool { return CheckShort(code) == nil }

// IsFull reports whether code is a valid full Open Location Code.
func IsFull(code string) bool { return CheckFull(code) == nil }

// StripCode removes separator and padding and uppercases alphabet characters.
// Result is truncated to maxCodeLen.
func StripCode(code string) string {
	var buf [maxCodeLen]byte
	n := stripInto(buf[:], code)
	return string(buf[:n])
}
