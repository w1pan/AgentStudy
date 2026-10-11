import type { KcalRange } from '@/api/qingheng'

export const ENERGY_MIN = -600
export const ENERGY_MAX = 1000
export const ENERGY_SWEEP = 90
// Preserve the previous chord width and the apex at y = 50 as the arc flattens.
const HALF_WIDTH = 310 * Math.sin(Math.PI / 3)
export const ENERGY_RADIUS = HALF_WIDTH / Math.sin(ENERGY_SWEEP * Math.PI / 360)
export const ENERGY_CENTER = { x: 360, y: 50 + ENERGY_RADIUS }

export function energyAngle(value: number) {
  const fraction = Math.max(0, Math.min(1, (value - ENERGY_MIN) / (ENERGY_MAX - ENERGY_MIN)))
  return -90 - ENERGY_SWEEP / 2 + fraction * ENERGY_SWEEP
}

// A circular arc keeps the value scale proportional to arc length.
export function energyPoint(value: number, radius = ENERGY_RADIUS) {
  const angle = energyAngle(value) * Math.PI / 180
  return { x: ENERGY_CENTER.x + radius * Math.cos(angle), y: ENERGY_CENTER.y + radius * Math.sin(angle) }
}

export function energyArc(range: KcalRange, radius = ENERGY_RADIUS): string | null {
  if (range.high < ENERGY_MIN || range.low > ENERGY_MAX || range.low === range.high) return null
  const from = energyPoint(range.low, radius)
  const to = energyPoint(range.high, radius)
  return `M ${from.x} ${from.y} A ${radius} ${radius} 0 0 1 ${to.x} ${to.y}`
}
