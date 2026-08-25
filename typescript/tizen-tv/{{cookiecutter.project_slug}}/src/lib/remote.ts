import { type Dir, pickNext } from './spatial'

/** TV remote key codes. Arrows/Enter/Back work out of the box; the rest need registerKeys(). */
export const KEY = {
  LEFT: 37,
  UP: 38,
  RIGHT: 39,
  DOWN: 40,
  ENTER: 13,
  BACK: 10009,
  MEDIA_PLAY_PAUSE: 10252,
  RED: 403,
  GREEN: 404,
  YELLOW: 405,
  BLUE: 406,
} as const

const DIRS: Record<number, Dir> = { 37: 'left', 38: 'up', 39: 'right', 40: 'down' }

const FOCUSABLE = '[data-focusable]:not([disabled])'

/** Claim extra remote keys (media, colour buttons). No-op in a desktop browser. */
export function registerKeys(names: string[]): void {
  window.tizen?.tvinputdevice?.registerKeys(names)
}

/** Close the app — what BACK does on the root screen. No-op in a desktop browser. */
export function exitApp(): void {
  window.tizen?.application?.getCurrentApplication().exit()
}

function move(dir: Dir): void {
  const items = [...document.querySelectorAll<HTMLElement>(FOCUSABLE)]
  const active = document.activeElement as HTMLElement | null
  const from = active && items.includes(active) ? active : items[0]
  if (!from) return
  if (from !== active) {
    from.focus()
    return
  }
  const rest = items.filter((el) => el !== from)
  const boxes = rest.map((el) => el.getBoundingClientRect())
  const next = pickNext(from.getBoundingClientRect(), boxes, dir)
  if (next >= 0) rest[next].focus()
}

/**
 * Arrow keys move focus between `[data-focusable]` elements, BACK exits.
 * Returns a teardown — call it from `onMount`'s return or `$effect`'s cleanup.
 * `keyCode` is deprecated on the web but is what the TV platform sends.
 */
export function initRemote(): () => void {
  const onKeydown = (event: KeyboardEvent) => {
    const dir = DIRS[event.keyCode]
    if (dir) {
      event.preventDefault()
      move(dir)
      return
    }
    if (event.keyCode === KEY.BACK) exitApp()
  }
  window.addEventListener('keydown', onKeydown)
  return () => window.removeEventListener('keydown', onKeydown)
}
