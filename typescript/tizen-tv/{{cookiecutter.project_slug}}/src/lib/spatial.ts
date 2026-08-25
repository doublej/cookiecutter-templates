export type Dir = 'left' | 'right' | 'up' | 'down'

export interface Box {
  left: number
  right: number
  top: number
  bottom: number
}

/** Per direction: how far ahead a candidate lies, and how far off-axis. */
const AXIS: Record<Dir, (dx: number, dy: number) => [number, number]> = {
  left: (dx, dy) => [-dx, Math.abs(dy)],
  right: (dx, dy) => [dx, Math.abs(dy)],
  up: (dx, dy) => [-dy, Math.abs(dx)],
  down: (dx, dy) => [dy, Math.abs(dx)],
}

const centre = (b: Box) => ({ x: (b.left + b.right) / 2, y: (b.top + b.bottom) / 2 })

/**
 * Index of the nearest candidate lying in `dir` from `from`, or -1 when nothing does.
 * Off-axis distance is weighted double, so straight-ahead beats diagonal.
 */
export function pickNext(from: Box, candidates: Box[], dir: Dir): number {
  const a = centre(from)
  const project = AXIS[dir]
  let best = -1
  let bestScore = Number.POSITIVE_INFINITY
  for (let i = 0; i < candidates.length; i++) {
    const b = centre(candidates[i])
    const [ahead, off] = project(b.x - a.x, b.y - a.y)
    if (ahead <= 0) continue
    const score = ahead + off * 2
    if (score < bestScore) {
      bestScore = score
      best = i
    }
  }
  return best
}
