package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"time"
)

// run starts the HTTP server and blocks until ctx is cancelled, then drains.
func run(ctx context.Context, logger *slog.Logger, addr string) error {
	srv := &http.Server{Addr: addr, Handler: routes(logger)}
	go func() {
		<-ctx.Done()
		shutdown(srv, logger)
	}()
	logger.Info("listening", "addr", addr)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

// shutdown gracefully drains in-flight requests with a timeout.
func shutdown(srv *http.Server, logger *slog.Logger) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		logger.Error("shutdown", "err", err)
	}
}

// routes wires the request multiplexer.
func routes(logger *slog.Logger) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", handleHealth)
	mux.HandleFunc("GET /", handleRoot(logger))
	return mux
}

// handleHealth reports liveness as JSON.
func handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintln(w, `{"status":"ok"}`)
}

// handleRoot is the default greeting handler.
func handleRoot(logger *slog.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		logger.Info("request", "method", r.Method, "path", r.URL.Path)
		fmt.Fprintln(w, "{{ cookiecutter.project_name }} is running")
	}
}
