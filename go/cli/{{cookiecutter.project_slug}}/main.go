// Command {{ cookiecutter.project_slug }} is {{ cookiecutter.description }}.
package main

import (
	"errors"
	"flag"
	"fmt"
	"os"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

// run parses flags and dispatches. Returns nil on -h/--help.
func run(args []string) error {
	fs := flag.NewFlagSet("{{ cookiecutter.project_slug }}", flag.ContinueOnError)
	verbose := fs.Bool("verbose", false, "enable verbose output")
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}
	return process(fs.Args(), *verbose)
}

// process handles the parsed positional inputs.
func process(inputs []string, verbose bool) error {
	if len(inputs) == 0 {
		fmt.Println("No input provided. Use --help for usage.")
		return nil
	}
	if verbose {
		fmt.Printf("processing %d input(s)\n", len(inputs))
	}
	for _, in := range inputs {
		fmt.Println("Processing:", in)
	}
	return nil
}
