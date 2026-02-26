// Copyright 2026 AumOS Enterprise
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

package aumos

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"time"
)

const (
	defaultBaseURL     = "https://api.aumos.io/v1"
	defaultTimeout     = 30 * time.Second
	defaultMaxRetries  = 3
	sdkVersion         = "1.0.0"
)

// ClientOption is a functional option for configuring a Client.
type ClientOption func(*Client)

// WithAPIKey sets the API key used for authentication.
func WithAPIKey(key string) ClientOption {
	return func(c *Client) { c.apiKey = key }
}

// WithBaseURL overrides the default API base URL.
func WithBaseURL(baseURL string) ClientOption {
	return func(c *Client) { c.baseURL = baseURL }
}

// WithTimeout sets the HTTP request timeout.
func WithTimeout(d time.Duration) ClientOption {
	return func(c *Client) { c.httpClient.Timeout = d }
}

// WithMaxRetries sets the maximum number of retry attempts for transient errors.
func WithMaxRetries(n int) ClientOption {
	return func(c *Client) { c.maxRetries = n }
}

// WithHTTPClient replaces the underlying http.Client.
func WithHTTPClient(hc *http.Client) ClientOption {
	return func(c *Client) { c.httpClient = hc }
}

// Client is the AumOS Enterprise API client.
//
// Create a client with NewClient and reuse it across goroutines — it is safe
// for concurrent use.
//
//	client, err := aumos.NewClient()
//	if err != nil {
//	    log.Fatal(err)
//	}
//	agent, err := client.Agents.Create(ctx, aumos.CreateAgentRequest{
//	    Name:    "my-agent",
//	    ModelID: "aumos:claude-opus-4-6",
//	})
type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
	maxRetries int

	Agents     *AgentsService
	Runs       *RunsService
	Models     *ModelsService
	Governance *GovernanceService
}

// NewClient constructs a new AumOS API client.
//
// The API key is resolved in order: explicit WithAPIKey option, then the
// AUMOS_API_KEY environment variable.
//
// Returns an error if no API key can be found.
func NewClient(opts ...ClientOption) (*Client, error) {
	c := &Client{
		baseURL: defaultBaseURL,
		httpClient: &http.Client{
			Timeout: defaultTimeout,
		},
		maxRetries: defaultMaxRetries,
	}

	for _, opt := range opts {
		opt(c)
	}

	if c.apiKey == "" {
		c.apiKey = os.Getenv("AUMOS_API_KEY")
	}
	if c.apiKey == "" {
		return nil, errors.New(
			"aumos: no API key configured — pass WithAPIKey() or set AUMOS_API_KEY",
		)
	}

	c.Agents = &AgentsService{client: c}
	c.Runs = &RunsService{client: c}
	c.Models = &ModelsService{client: c}
	c.Governance = &GovernanceService{client: c}

	return c, nil
}

// Health checks the platform health. This endpoint does not require
// authentication and is suitable for readiness probes.
func (c *Client) Health(ctx context.Context) (*HealthResponse, error) {
	var result HealthResponse
	if err := c.do(ctx, http.MethodGet, "/health", nil, &result, false); err != nil {
		return nil, err
	}
	return &result, nil
}

// do executes an HTTP request and decodes the JSON response into out.
// If out is nil, the response body is discarded (e.g. for DELETE 204).
func (c *Client) do(
	ctx context.Context,
	method string,
	path string,
	body interface{},
	out interface{},
	authenticated bool,
) error {
	var lastErr error

	for attempt := 0; attempt <= c.maxRetries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(1<<uint(attempt-1)) * time.Second
			if backoff > 30*time.Second {
				backoff = 30 * time.Second
			}
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
			}
		}

		err := c.doOnce(ctx, method, path, body, out, authenticated)
		if err == nil {
			return nil
		}

		var apiErr *APIError
		if errors.As(err, &apiErr) {
			// Retry on transient server errors and rate limits
			switch apiErr.StatusCode {
			case http.StatusTooManyRequests,
				http.StatusInternalServerError,
				http.StatusBadGateway,
				http.StatusServiceUnavailable,
				http.StatusGatewayTimeout:
				lastErr = err
				continue
			}
		}
		return err
	}

	return lastErr
}

func (c *Client) doOnce(
	ctx context.Context,
	method string,
	path string,
	body interface{},
	out interface{},
	authenticated bool,
) error {
	var bodyReader io.Reader
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("aumos: marshal request: %w", err)
		}
		bodyReader = bytes.NewReader(encoded)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bodyReader)
	if err != nil {
		return fmt.Errorf("aumos: build request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "aumos-go-sdk/"+sdkVersion)

	if authenticated {
		req.Header.Set("X-API-Key", c.apiKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("aumos: send request: %w", err)
	}
	defer resp.Body.Close() //nolint:errcheck

	requestID := resp.Header.Get("X-Request-ID")

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		if out == nil || resp.StatusCode == http.StatusNoContent {
			return nil
		}
		if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
			return fmt.Errorf("aumos: decode response: %w", err)
		}
		return nil
	}

	// Parse error body
	var errBody struct {
		Error   string                 `json:"error"`
		Message string                 `json:"message"`
		Details map[string]interface{} `json:"details"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&errBody)

	return &APIError{
		StatusCode: resp.StatusCode,
		ErrorCode:  errBody.Error,
		Message:    errBody.Message,
		Details:    errBody.Details,
		RequestID:  requestID,
	}
}

// buildURL appends query parameters to a path string.
func buildURL(path string, params map[string]string) string {
	if len(params) == 0 {
		return path
	}
	query := url.Values{}
	for k, v := range params {
		if v != "" {
			query.Set(k, v)
		}
	}
	return path + "?" + query.Encode()
}

// ---------------------------------------------------------------------------
// AgentsService
// ---------------------------------------------------------------------------

// AgentsService provides methods for managing agents.
type AgentsService struct{ client *Client }

// List returns a paginated list of agents.
func (s *AgentsService) List(ctx context.Context, opts ListAgentsOptions) (*AgentListResponse, error) {
	params := map[string]string{}
	if opts.Status != "" {
		params["status"] = string(opts.Status)
	}
	if opts.PageSize > 0 {
		params["pageSize"] = strconv.Itoa(opts.PageSize)
	}
	if opts.PageToken != "" {
		params["pageToken"] = opts.PageToken
	}

	var result AgentListResponse
	if err := s.client.do(ctx, http.MethodGet, buildURL("/agents", params), nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// Create creates a new agent.
func (s *AgentsService) Create(ctx context.Context, req CreateAgentRequest) (*Agent, error) {
	var result Agent
	if err := s.client.do(ctx, http.MethodPost, "/agents", req, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// Get retrieves a single agent by ID.
func (s *AgentsService) Get(ctx context.Context, agentID string) (*Agent, error) {
	var result Agent
	if err := s.client.do(ctx, http.MethodGet, "/agents/"+agentID, nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// Update partially updates an agent.
func (s *AgentsService) Update(ctx context.Context, agentID string, req UpdateAgentRequest) (*Agent, error) {
	var result Agent
	if err := s.client.do(ctx, http.MethodPatch, "/agents/"+agentID, req, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// Delete deletes an agent (soft delete).
func (s *AgentsService) Delete(ctx context.Context, agentID string) error {
	return s.client.do(ctx, http.MethodDelete, "/agents/"+agentID, nil, nil, true)
}

// CreateRun starts a new run for the given agent.
func (s *AgentsService) CreateRun(ctx context.Context, agentID string, req CreateRunRequest) (*Run, error) {
	var result Run
	if err := s.client.do(ctx, http.MethodPost, "/agents/"+agentID+"/runs", req, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListRuns returns paginated runs for an agent.
func (s *AgentsService) ListRuns(ctx context.Context, agentID string, opts ListRunsOptions) (*RunListResponse, error) {
	params := map[string]string{}
	if opts.PageSize > 0 {
		params["pageSize"] = strconv.Itoa(opts.PageSize)
	}
	if opts.PageToken != "" {
		params["pageToken"] = opts.PageToken
	}

	var result RunListResponse
	path := buildURL("/agents/"+agentID+"/runs", params)
	if err := s.client.do(ctx, http.MethodGet, path, nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// WaitForRun polls a run until it reaches a terminal status.
//
// pollInterval controls how often to check; maxWait is the total deadline.
// ctx cancellation is also respected.
func (s *AgentsService) WaitForRun(
	ctx context.Context,
	agentID string,
	runID string,
	pollInterval time.Duration,
	maxWait time.Duration,
) (*Run, error) {
	if pollInterval == 0 {
		pollInterval = 2 * time.Second
	}
	if maxWait == 0 {
		maxWait = 5 * time.Minute
	}

	deadline := time.Now().Add(maxWait)

	for {
		run, err := s.client.Runs.Get(ctx, runID)
		if err != nil {
			return nil, err
		}
		if run.IsTerminal() {
			return run, nil
		}

		if time.Now().After(deadline) {
			return nil, fmt.Errorf("aumos: run %s did not complete within %s", runID, maxWait)
		}

		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(pollInterval):
		}
	}
}

// ---------------------------------------------------------------------------
// RunsService
// ---------------------------------------------------------------------------

// RunsService provides methods for querying runs.
type RunsService struct{ client *Client }

// Get retrieves a run by ID.
func (s *RunsService) Get(ctx context.Context, runID string) (*Run, error) {
	var result Run
	if err := s.client.do(ctx, http.MethodGet, "/runs/"+runID, nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// ---------------------------------------------------------------------------
// ModelsService
// ---------------------------------------------------------------------------

// ModelsService provides methods for querying the model registry.
type ModelsService struct{ client *Client }

// List returns models available to the tenant.
func (s *ModelsService) List(ctx context.Context, opts ListModelsOptions) (*ModelListResponse, error) {
	params := map[string]string{}
	if opts.Provider != "" {
		params["provider"] = opts.Provider
	}
	if opts.PageSize > 0 {
		params["pageSize"] = strconv.Itoa(opts.PageSize)
	}
	if opts.PageToken != "" {
		params["pageToken"] = opts.PageToken
	}

	var result ModelListResponse
	if err := s.client.do(ctx, http.MethodGet, buildURL("/models", params), nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// Get retrieves a model by ID.
func (s *ModelsService) Get(ctx context.Context, modelID string) (*Model, error) {
	var result Model
	if err := s.client.do(ctx, http.MethodGet, "/models/"+modelID, nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// ---------------------------------------------------------------------------
// GovernanceService
// ---------------------------------------------------------------------------

// GovernanceService provides methods for governance policies and audit logs.
type GovernanceService struct{ client *Client }

// ListPolicies returns all governance policies for the tenant.
func (s *GovernanceService) ListPolicies(ctx context.Context) (*PolicyListResponse, error) {
	var result PolicyListResponse
	if err := s.client.do(ctx, http.MethodGet, "/governance/policies", nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListAuditLogs retrieves audit log entries with optional filters.
func (s *GovernanceService) ListAuditLogs(ctx context.Context, opts ListAuditLogsOptions) (*AuditLogListResponse, error) {
	params := map[string]string{}
	if opts.PageSize > 0 {
		params["pageSize"] = strconv.Itoa(opts.PageSize)
	}
	if opts.PageToken != "" {
		params["pageToken"] = opts.PageToken
	}
	if opts.StartTime != "" {
		params["startTime"] = opts.StartTime
	}
	if opts.EndTime != "" {
		params["endTime"] = opts.EndTime
	}
	if opts.Action != "" {
		params["action"] = opts.Action
	}

	var result AuditLogListResponse
	path := buildURL("/governance/audit-logs", params)
	if err := s.client.do(ctx, http.MethodGet, path, nil, &result, true); err != nil {
		return nil, err
	}
	return &result, nil
}
