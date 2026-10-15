package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"{{ cookiecutter.project_slug }}/internal/i18n"
)

// run starts the HTTP server and blocks until ctx is cancelled, then drains.
func run(ctx context.Context, logger *slog.Logger, addr string) error {
	srv := &http.Server{
		Addr:              addr,
		Handler:           routes(logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
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

// routes wires the request multiplexer behind the locale middleware.
func routes(logger *slog.Logger) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", handleHealth)
	mux.HandleFunc("GET /", handleRoot(logger))
	return withLocale(mux)
}

type localeKey struct{}

// withLocale negotiates the response language from Accept-Language into the request context.
func withLocale(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		locale := i18n.Negotiate(r.Header.Get("Accept-Language"))
		w.Header().Set("Content-Language", locale)
		w.Header().Add("Vary", "Accept-Language")
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), localeKey{}, locale)))
	})
}

// localeOf returns the locale withLocale stored; an empty one falls back to en in i18n.T.
func localeOf(r *http.Request) string {
	locale, _ := r.Context().Value(localeKey{}).(string)
	return locale
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
		fmt.Fprintln(w, i18n.T(localeOf(r), "running", "name", "{{ cookiecutter.project_name }}"))
	}
}
