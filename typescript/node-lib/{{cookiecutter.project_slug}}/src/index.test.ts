import { describe, expect, it } from 'vitest'
import { add, greet } from './index.js'

describe('greet', () => {
  it('returns a friendly greeting', () => {
    expect(greet('World')).toBe('Hello, World!')
  })
})

describe('add', () => {
  it('adds two numbers', () => {
    expect(add(2, 3)).toBe(5)
  })
})
