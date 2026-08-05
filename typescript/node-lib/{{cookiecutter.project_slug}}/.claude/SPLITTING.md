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

- the parts would import each other in a **cycle**;
- the file has **top-level statements** outside any declaration (side effects it cannot place);
- the file has a **default export** (moving it would change the surface subtly);
- a **target path already exists**;
- the file has **uncommitted changes** — commit first so `git diff` shows only the split, or
  pass `--force` if you accept the mixed diff.

Each of these is a case where a human decision is cheaper than an automated guess.

## Scope

`.ts` only, top-level declarations only. Decorators, `declare module` blocks, and JSX are
outside what the scanner handles. Test files are not special-cased — an oversized test file
usually wants splitting by *scenario*, which the reference graph cannot see, so treat its
proposal with extra suspicion.
