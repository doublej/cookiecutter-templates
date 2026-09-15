package main

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthz(t *testing.T) {
	rec := serve(t, http.MethodGet, "/healthz", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /healthz = %d, want 200", rec.Code)
	}
}

func TestRoot(t *testing.T) {
	rec := serve(t, http.MethodGet, "/", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET / = %d, want 200", rec.Code)
	}
}

func TestRootNegotiatesLanguage(t *testing.T) {
	en := serve(t, http.MethodGet, "/", "")
	nl := serve(t, http.MethodGet, "/", "nl-NL,nl;q=0.9,en;q=0.8")
	if got := en.Header().Get("Content-Language"); got != "en" {
		t.Errorf("no Accept-Language: Content-Language = %q, want en", got)
	}
	if got := nl.Header().Get("Content-Language"); got != "nl" {
		t.Errorf("Accept-Language nl: Content-Language = %q, want nl", got)
	}
	if got := nl.Header().Get("Vary"); got != "Accept-Language" {
		t.Errorf("Vary = %q, want Accept-Language", got)
	}
	if nl.Body.String() == en.Body.String() {
		t.Errorf("nl body %q equals en body", nl.Body.String())
	}
}

// serve runs one request through the router and returns the recorder.
func serve(t *testing.T, method, target, acceptLanguage string) *httptest.ResponseRecorder {
	t.Helper()
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	req := httptest.NewRequest(method, target, nil)
	req.Header.Set("Accept-Language", acceptLanguage)
	rec := httptest.NewRecorder()
	routes(logger).ServeHTTP(rec, req)
	return rec
}
