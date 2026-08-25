{%- set chrome = {"6.0": "chrome76", "7.0": "chrome94", "8.0": "chrome108"}[cookiecutter.tizen_required_version] -%}
import { sveltekit } from '@sveltejs/kit/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [sveltekit()],
  // Tizen {{ cookiecutter.tizen_required_version }} ships an old Chromium — bump this
  // together with tizen_required_version in config.xml, never separately.
  build: { target: '{{ chrome }}' },
})
