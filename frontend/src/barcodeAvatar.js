// Same technique as public/favicon.svg: each character's ASCII code as a
// 3-digit triplet, rendered as UPC-A-style bars. The favicon hand-encodes a
// fixed 4-letter word (HBCS) using real UPC-A's split left/right-half parity
// encoding; profile names are arbitrary length, so this generalizes it by
// encoding the full digit run continuously with the left-hand (L-code)
// digit patterns throughout, bounded by start/end guard bars - visually the
// same "barcode" look, without real UPC-A's fixed-12-digit structure (moot
// here since this is decorative, not meant to be scanned).

const L_CODE = {
  0: '0001101',
  1: '0011001',
  2: '0010011',
  3: '0111101',
  4: '0100011',
  5: '0110001',
  6: '0101111',
  7: '0111011',
  8: '0110111',
  9: '0001011',
}

const GUARD = '101'

function nameToDigits(name) {
  return name
    .split('')
    .map((c) => String(c.codePointAt(0) % 1000).padStart(3, '0'))
    .join('')
}

/**
 * Returns { bars: [{x, width}], totalModules } describing black bars for
 * `name`, in module units (1 module = the narrowest bar width).
 */
export function barcodeBarsForName(name) {
  const digits = nameToDigits(name)
  const pattern = GUARD + [...digits].map((d) => L_CODE[d]).join('') + GUARD

  const bars = []
  let x = 0
  let runStart = null
  for (let i = 0; i < pattern.length; i++) {
    if (pattern[i] === '1') {
      if (runStart === null) runStart = x
    } else if (runStart !== null) {
      bars.push({ x: runStart, width: x - runStart })
      runStart = null
    }
    x += 1
  }
  if (runStart !== null) bars.push({ x: runStart, width: x - runStart })

  return { bars, totalModules: pattern.length }
}
