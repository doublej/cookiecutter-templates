import { describe, expect, test } from 'bun:test'
import { add, greet } from './index.js'

describe('greet', () => {
  test('returns a friendly greeting', () => {
    expect(greet('Bun')).toBe('Hello, Bun!')
  })
})

describe('add', () => {
  test('adds two numbers', () => {
    expect(add(2, 3)).toBe(5)
  })
})
