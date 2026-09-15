package main

import "testing"

func TestProcessNoInput(t *testing.T) {
	if err := process(nil, false, "en"); err != nil {
		t.Fatalf("process(nil) = %v, want nil", err)
	}
}

func TestProcessWithInputs(t *testing.T) {
	if err := process([]string{"a", "b"}, true, "nl"); err != nil {
		t.Fatalf("process([a b]) = %v, want nil", err)
	}
}

func TestRunHelp(t *testing.T) {
	if err := run([]string{"-h"}); err != nil {
		t.Fatalf("run(-h) = %v, want nil", err)
	}
}

func TestResolveLocaleFlagBeatsEnv(t *testing.T) {
	t.Setenv("LC_ALL", "")
	t.Setenv("LC_MESSAGES", "")
	t.Setenv("LANG", "nl_NL.UTF-8")
	if got := resolveLocale(""); got != "nl" {
		t.Errorf("resolveLocale(\"\") with LANG=nl_NL.UTF-8 = %q, want nl", got)
	}
	if got := resolveLocale("en"); got != "en" {
		t.Errorf("resolveLocale(\"en\") with LANG=nl_NL.UTF-8 = %q, want en", got)
	}
}
