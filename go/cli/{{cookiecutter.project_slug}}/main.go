// Command {{ cookiecutter.project_slug }} is {{ cookiecutter.description }}.
package main

import (
	"errors"
	"flag"
	"fmt"
	"os"
	"strings"

	"{{ cookiecutter.project_slug }}/internal/i18n"
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
	lang := fs.String("lang", "", "output language: "+strings.Join(i18n.Supported(), ", ")+" (default: LC_ALL, LC_MESSAGES, LANG)")
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}
	return process(fs.Args(), *verbose, resolveLocale(*lang))
}

// resolveLocale picks the output language: the -lang flag, then the environment, then en.
func resolveLocale(flagValue string) string {
	if flagValue != "" {
		return i18n.Normalize(flagValue)
	}
	return i18n.FromEnv()
}

// process handles the parsed positional inputs, printing in locale.
func process(inputs []string, verbose bool, locale string) error {
	if len(inputs) == 0 {
		fmt.Println(i18n.T(locale, "no_input"))
		return nil
	}
	if verbose {
		fmt.Println(i18n.N(locale, "input_count", len(inputs)))
	}
	for _, in := range inputs {
		fmt.Println(i18n.T(locale, "processing", "input", in))
	}
	return nil
}
