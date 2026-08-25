/**
 * Ambient types for the slice of the Tizen device API this app touches.
 * `window.tizen` is undefined in a desktop browser — always optional-chain it.
 * Anything beyond this (avplay, productinfo, …) lives on `window.webapis` and
 * needs `<script src="$WEBAPIS/webapis/webapis.js">` injected into the page.
 */
declare global {
  interface Window {
    tizen?: {
      tvinputdevice?: {
        registerKey(name: string): void
        registerKeys(names: string[]): void
        unregisterKey(name: string): void
      }
      application?: {
        getCurrentApplication(): { exit(): void }
      }
    }
  }
}

export {}
