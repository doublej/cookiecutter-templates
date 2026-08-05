# Splitting oversized modules

`just loc-check` fails a file at `.quality.json`'s `loc.error`. This is how to fix it.
`just loc-fix` prints a proposal; it never writes unless you pass `--apply`.

## Why the limit exists

The limit is not about aesthetics. A module you can hold in your head has one reason to
change; a 400-line one has several, and every edit to it risks the others. The number is a
proxy for that — it is deliberately crude, because a precise rule would be argued with.

So the fix is never "make the file shorter". Deleting comments, collapsing whitespace, or
inlining helpers to duck under the threshold makes the file *worse* and the check *pass* —
the exact failure mode the limit exists to prevent. If a file is over, it has more than one
job. Find the jobs.

## How to pick seams

Split along the **reference graph**, not the line count. Two declarations that call each
other belong in the same module; two that never mention each other are already separate
modules that happen to share a file.

`just loc-fix` computes this for you: it groups top-level declarations into connected
components (A references B → same group), then names each group after its leading export.
Read the grouping before you trust it. Good signs:

- Each group has a name you would have chosen yourself (`parse`, `types`, `render`).
- The types group is genuinely types — not one type dragged along by a helper.
- No group is "everything else".

**Reject the proposal** when the groups come out as one giant cluster plus scraps. That
means the file has no natural seam yet, and the honest fix is a design change — extract an
interface, invert a dependency, or move a concern out entirely — before any mechanical
split. A tool cannot do that for you, and a bad split is harder to undo than a long file.

## When one declaration is the whole file

Rearranging top-level declarations cannot help a file whose single class (or data
literal) is bigger than `loc.error` on its own. For that case `just loc-fix` switches
strategy and splits by **members** instead:

**Giant class.** Private instance methods move out as free functions that take the
instance first — `private endRound(id)` becomes `export function endRound(self: TheClass,
id)`, and every `this.` inside becomes `self.`. The class stays in the original file as a
facade: fields, the constructor, public methods, and anything the scanner cannot move
safely (each is listed with its reason in the proposal). Callers inside the class are
rewritten from `this.endRound(id)` to `endRound(this, id)`. A method that never touches
`this` becomes a plain function with no `self` parameter.

Three consequences to review before applying:

- **Widening.** A private member that an extracted function touches loses its `private`
  modifier — the class type gets wider. The proposal lists every widened name. This is
  the same trade a hand split makes; the package barrel (`index.ts`) is unchanged either
  way, so nothing new becomes *package* public.
- **Support parts.** File-private types and constants the parts need move to `types.ts` /
  `constants.ts` parts (merged into one `support.ts` when dir-check leaves no room).
  Anything that must stay in the facade but is needed by a part gets promoted
  (`export`ed from the facade, still absent from the barrel).
- **Cycles between method parts are fine here** — unlike the top-level split. The parts
  contain nothing but hoisted function declarations, so their mutual imports are only
  dereferenced at call time, never during module evaluation. The class type flows the
  other way as an `import type`, which is erased.

**Giant data literal.** A `const X: T[] = [...]` splits by elements into part arrays
(`X_1`, `X_2`, …) and the facade reassembles them: `export const X: T[] = [...X_1, ...X_2]`.
The parts carry the same `T[]` annotation, so element contextual typing (literal unions,
excess-property checks) survives. This only works for **annotated arrays** — an
un-annotated array or an object literal is refused, because re-inferred element types
widen (`'feature'` becomes `string`) and object spreads evaluate getters.

**Public methods and delegating stubs.** When private-only extraction leaves the facade
still over the limit, public method bodies move out too — but a public method cannot
simply vanish from the class, so a **stub** stays behind: the original signature with
the body replaced by `return name(this, ...args)`. The instance type is unchanged
character-for-character; only the body lives elsewhere. This needs every parameter to be
a plain (optionally rest/optional/defaulted) identifier — a destructured or `this`-typed
parameter cannot be forwarded, and such methods stay whole. Stubs also survive being
referenced without a call (`this.f.bind(this)` still finds a real method), so the usual
pinning rules do not apply to them.

What stays in the class no matter what: getters/setters, statics, decorated members,
overload sets, `#private` fields and their users, `super` users, methods that declare
their own `this` scope (a `function` expression or nested class), methods referenced
without a call (`this.f.bind(this)`) unless stubbed, dynamic imports, `import.meta`
users (its value is per-module), and — on an `extends` class —
any method touching an inherited member (`this.ctx` on a Durable Object, `this.emit` on
an EventEmitter): the scanner cannot know if it is `protected` upstream. If nothing is
movable, the tool says so and the fix is a design change, as above.

## `dir-check` fights `loc-check`

Splitting one file into three siblings adds two files to a directory that `just dir-check`
caps at `dir.max_files`. Satisfying `loc-check` this way can break `dir-check` in the same
commit, which is why the proposal picks a layout rather than always writing siblings:

| Room in the directory | Layout | Result |
|---|---|---|
| `current + parts <= max_files` | siblings | `src/foo-types.ts`, `src/foo-parse.ts`, `src/foo.ts` as barrel |
| otherwise | subdirectory | `src/foo/types.ts`, `src/foo/parse.ts`, `src/foo.ts` as barrel |

The subdirectory layout leaves the parent's file count unchanged, so it always satisfies
`dir-check` as long as the parts themselves fit under `max_files`. Both layouts stay inside
the `src/**/*.ts` glob, so both are still checked.

## Splitting must not widen the public surface

This library's invariant: **everything public lives in `index.ts`; internals stay in sibling
modules and are not re-exported.** Splitting threatens that in a way that is easy to miss.

A file-private helper is private because nothing outside the file can see it. Move it to its
own module and a sibling still needs it — so it has to become `export`ed. It is now *module*
public. If the barrel then does `export * from './foo-parse.js'`, it is *package* public, and
you have shipped an internal helper as API without deciding to.

So:

- The barrel re-exports **explicit named symbols**, never `export *`.
- It lists exactly the names that were exported before the split — no more.
- A symbol that was file-private gets `export` in its new module (siblings need it) and is
  **absent from the barrel**.

`just loc-fix` marks file-private symbols with `*` in its proposal and follows this rule when
applying. After an `--apply`, `git diff` the barrel: it should account for every name the old
file exported, and introduce none.

One class of declarations never moves at all: anything reading **`import.meta`** (and, by
extension, anything referencing such a declaration). `import.meta.url` is per-module, so a
moved copy would resolve to the wrong file. Those blocks stay in the barrel — the proposal
lists them under "pinned to the barrel" — and the parts hold everything else. This is safe
because the barrel's imports (the parts) evaluate before its own body, and nothing in a
part is allowed to reference a pinned name.

## After `--apply`

```
just lint-fix   # Biome drops the imports the new modules do not use, and reorders the rest
just check      # loc-check + dir-check + lint + typecheck + test
```

`typecheck` is the real gate. The proposal comes from a brace-depth line scanner, not a
TypeScript parser, so a green `tsc` is what proves the import rewriting is correct. If it is
red, `git checkout` the split and do it by hand — the file was outside what the scanner
understands.

## What the tool refuses to do

It prints the proposal but declines to write when:

- the parts would import each other in a **cycle** (unless every part on the cycle holds
  only hoisted declarations);
- the file has **top-level statements** interleaved between declarations (side effects it
  cannot place) — statements *after* the last declaration stay in the barrel, which the
  parts' imports still evaluate first;
- the file has a **default export** (moving it would change the surface subtly);
- a **target path already exists**;
- a giant class has **no safely movable member**, a giant array is **un-annotated**, or a
  giant data literal is an **object literal** (see above);
- the file has **uncommitted changes** — commit first so `git diff` shows only the split, or
  pass `--force` if you accept the mixed diff.

Each of these is a case where a human decision is cheaper than an automated guess.

## Scope

`.ts` only. Top-level declarations, plus member extraction for one giant class or
annotated array per file. Decorators, `declare module` blocks, and JSX are
outside what the scanner handles. Test files are not special-cased — an oversized test file
usually wants splitting by *scenario*, which the reference graph cannot see, so treat its
proposal with extra suspicion.
