package main

import "testing"

func TestProcessNoInput(t *testing.T) {
	if err := process(nil, false); err != nil {
		t.Fatalf("process(nil) = %v, want nil", err)
	}
}

func TestProcessWithInputs(t *testing.T) {
	if err := process([]string{"a", "b"}, true); err != nil {
		t.Fatalf("process([a b]) = %v, want nil", err)
	}
}

func TestRunHelp(t *testing.T) {
	if err := run([]string{"-h"}); err != nil {
		t.Fatalf("run(-h) = %v, want nil", err)
	}
}
