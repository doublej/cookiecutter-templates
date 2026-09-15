// Package i18n looks up user-facing text by key in the embedded language files
// locales/<locale>.json. Base (en) holds the source strings and is the fallback.
//
// Keys are flat ("no_input"). A message is a string with {name} placeholders or a
// plural object {"one": "…", "other": "…"}. Adding a language = adding
// locales/<locale>.json; the embed pattern registers it.
package i18n

import (
	"embed"
	"encoding/json"
	"fmt"
	"maps"
	"os"
	"slices"
	"strconv"
	"strings"
)

// Base is the source language and the fallback for unsupported locales and missing keys.
const Base = "en"

//go:embed locales/*.json
var localeFiles embed.FS

var catalogs = loadCatalogs()

// loadCatalogs parses every embedded language file. A broken file is a developer
// error the first test run catches, so it panics instead of returning an error.
func loadCatalogs() map[string]map[string]any {
	names, err := localeFiles.ReadDir("locales")
	if err != nil {
		panic(err)
	}
	out := make(map[string]map[string]any, len(names))
	for _, entry := range names {
		data, err := localeFiles.ReadFile("locales/" + entry.Name())
		if err != nil {
			panic(err)
		}
		var messages map[string]any
		if err := json.Unmarshal(data, &messages); err != nil {
			panic(fmt.Errorf("i18n: locales/%s: %w", entry.Name(), err))
		}
		out[strings.TrimSuffix(entry.Name(), ".json")] = messages
	}
	return out
}

// Supported returns the available locales, sorted.
func Supported() []string {
	return slices.Sorted(maps.Keys(catalogs))
}

// Normalize maps a locale tag such as "nl_NL.UTF-8", "nl-BE" or "NL" to a supported
// locale. Empty, C, POSIX and unsupported tags give Base.
func Normalize(tag string) string {
	if locale, ok := match(tag); ok {
		return locale
	}
	return Base
}

// match reduces tag to its lowercase language subtag and reports whether it is supported.
func match(tag string) (string, bool) {
	lang, _, _ := strings.Cut(strings.TrimSpace(tag), ".")
	lang, _, _ = strings.Cut(strings.ReplaceAll(lang, "_", "-"), "-")
	lang = strings.ToLower(lang)
	_, ok := catalogs[lang]
	return lang, ok
}

// FromEnv resolves the locale from LC_ALL, LC_MESSAGES, then LANG. As in POSIX, the
// first non-empty variable decides, so LC_ALL=C gives Base even when LANG is set.
func FromEnv() string {
	for _, name := range []string{"LC_ALL", "LC_MESSAGES", "LANG"} {
		if value := os.Getenv(name); value != "" {
			return Normalize(value)
		}
	}
	return Base
}

// Negotiate picks the supported locale with the highest q-value from an
// Accept-Language header ("nl-NL,nl;q=0.9,en;q=0.8"). Ties keep header order;
// no match gives Base.
func Negotiate(header string) string {
	best, bestQ := Base, 0.0
	for _, part := range strings.Split(header, ",") {
		tag, params, _ := strings.Cut(part, ";")
		locale, ok := match(tag)
		if q := quality(params); ok && q > bestQ {
			best, bestQ = locale, q
		}
	}
	return best
}

// quality parses the q parameter of one Accept-Language entry: absent means 1, malformed means 0.
func quality(params string) float64 {
	name, value, found := strings.Cut(params, "=")
	if !found || strings.TrimSpace(name) != "q" {
		return 1
	}
	q, err := strconv.ParseFloat(strings.TrimSpace(value), 64)
	if err != nil {
		return 0
	}
	return q
}

// T returns the message for key in locale with {name} placeholders filled from args,
// given as name/value pairs like log/slog: T(locale, "greeting", "name", "Ada").
// A key missing in locale falls back to Base, then to the key itself.
func T(locale, key string, args ...any) string {
	text, ok := find(locale, key).(string)
	if !ok {
		return key
	}
	return fill(text, args)
}

// N is T for a plural message: it picks the one/other form by count and fills {count}.
func N(locale, key string, count int, args ...any) string {
	forms, _ := find(locale, key).(map[string]any)
	// ponytail: one/other only — correct for en and nl; add CLDR plural rules with the first language that needs more
	form := "other"
	if count == 1 {
		form = "one"
	}
	text, ok := forms[form].(string)
	if !ok {
		return key
	}
	return fill(text, append([]any{"count", count}, args...))
}

// find returns the raw message for key in locale, falling back to Base, or nil.
func find(locale, key string) any {
	if message, ok := catalogs[locale][key]; ok {
		return message
	}
	return catalogs[Base][key]
}

// fill replaces every {name} in one pass, so a value containing braces is never re-filled.
func fill(text string, args []any) string {
	pairs := make([]string, 0, len(args))
	for i := 0; i+1 < len(args); i += 2 {
		pairs = append(pairs, "{"+fmt.Sprint(args[i])+"}", fmt.Sprint(args[i+1]))
	}
	return strings.NewReplacer(pairs...).Replace(text)
}
