package i18n

import (
	"slices"
	"testing"
)

// useFixture swaps in a small catalog for one test, so these tests don't break when copy changes.
func useFixture(t *testing.T) {
	t.Helper()
	saved := catalogs
	t.Cleanup(func() { catalogs = saved })
	catalogs = map[string]map[string]any{
		"en": {
			"greeting": "Hello {name}",
			"files":    map[string]any{"one": "{count} file in {dir}", "other": "{count} files in {dir}"},
			"only_en":  "English only",
		},
		"nl": {
			"greeting": "Hoi {name}",
			"files":    map[string]any{"one": "{count} bestand in {dir}", "other": "{count} bestanden in {dir}"},
		},
	}
}

func TestEmbeddedLocalesLoad(t *testing.T) {
	for _, locale := range []string{"en", "nl"} {
		if !slices.Contains(Supported(), locale) {
			t.Errorf("Supported() = %v, missing %q", Supported(), locale)
		}
	}
}

func TestNormalize(t *testing.T) {
	useFixture(t)
	cases := map[string]string{
		"nl_NL.UTF-8": "nl",
		"nl-BE":       "nl",
		"NL":          "nl",
		"en_US":       "en",
		"C":           "en",
		"POSIX":       "en",
		"fr_FR.UTF-8": "en",
		"":            "en",
	}
	for tag, want := range cases {
		if got := Normalize(tag); got != want {
			t.Errorf("Normalize(%q) = %q, want %q", tag, got, want)
		}
	}
}

func TestFromEnvOrder(t *testing.T) {
	useFixture(t)
	steps := []struct{ name, value, want string }{
		{"LANG", "", "en"},
		{"LANG", "nl_NL.UTF-8", "nl"},
		{"LC_MESSAGES", "C", "en"},
		{"LC_ALL", "nl_BE", "nl"},
	}
	t.Setenv("LC_ALL", "")
	t.Setenv("LC_MESSAGES", "")
	for _, step := range steps {
		t.Setenv(step.name, step.value)
		if got := FromEnv(); got != step.want {
			t.Errorf("after %s=%q FromEnv() = %q, want %q", step.name, step.value, got, step.want)
		}
	}
}

func TestNegotiate(t *testing.T) {
	useFixture(t)
	cases := map[string]string{
		"nl":                      "nl",
		"nl-NL,nl;q=0.9,en;q=0.8": "nl",
		"en;q=0.5, nl;q=0.8":      "nl",
		"fr-FR, nl;q=0.1":         "nl",
		"en, nl":                  "en",
		"nl;q=0":                  "en",
		"nl;q=abc":                "en",
		"fr, *":                   "en",
		"":                        "en",
	}
	for header, want := range cases {
		if got := Negotiate(header); got != want {
			t.Errorf("Negotiate(%q) = %q, want %q", header, got, want)
		}
	}
}

func TestTFallbackAndPlaceholders(t *testing.T) {
	useFixture(t)
	cases := []struct{ locale, key, want string }{
		{"nl", "greeting", "Hoi Ada"},
		{"en", "greeting", "Hello Ada"},
		{"fr", "greeting", "Hello Ada"},
		{"nl", "only_en", "English only"},
		{"nl", "missing", "missing"},
	}
	for _, c := range cases {
		if got := T(c.locale, c.key, "name", "Ada"); got != c.want {
			t.Errorf("T(%q, %q) = %q, want %q", c.locale, c.key, got, c.want)
		}
	}
}

func TestNPlural(t *testing.T) {
	useFixture(t)
	cases := []struct {
		locale string
		count  int
		want   string
	}{
		{"nl", 1, "1 bestand in src"},
		{"nl", 2, "2 bestanden in src"},
		{"nl", 0, "0 bestanden in src"},
		{"en", 1, "1 file in src"},
	}
	for _, c := range cases {
		if got := N(c.locale, "files", c.count, "dir", "src"); got != c.want {
			t.Errorf("N(%q, files, %d) = %q, want %q", c.locale, c.count, got, c.want)
		}
	}
	if got := N("nl", "greeting", 2); got != "greeting" {
		t.Errorf("N on a non-plural key = %q, want the key", got)
	}
}
