// Command {{ cookiecutter.project_slug }} is {{ cookiecutter.description }}.
package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	if err := run(ctx, logger, addr()); err != nil {
		logger.Error("server failed", "err", err)
		os.Exit(1)
	}
}

// addr returns the listen address from $PORT (default {{ cookiecutter.port }}).
func addr() string {
	port := os.Getenv("PORT")
	if port == "" {
		port = "{{ cookiecutter.port }}"
	}
	return ":" + port
}
