import { describe, expect, it } from 'vitest'
import { type Box, pickNext } from './spatial'

const box = (left: number, top: number): Box => ({
  left,
  top,
  right: left + 100,
  bottom: top + 100,
})

describe('pickNext', () => {
  const from = box(0, 0)
  const right = box(200, 0)
  const farRight = box(600, 0)
  const rightDown = box(200, 400)
  const below = box(0, 200)

  it('picks the nearest box in the direction of travel', () => {
    expect(pickNext(from, [farRight, right], 'right')).toBe(1)
    expect(pickNext(from, [right, below], 'down')).toBe(1)
  })

  it('prefers straight ahead over diagonal', () => {
    expect(pickNext(from, [rightDown, right], 'right')).toBe(1)
  })

  it('returns -1 when nothing lies that way', () => {
    expect(pickNext(from, [right, below], 'up')).toBe(-1)
    expect(pickNext(from, [], 'right')).toBe(-1)
  })
})
