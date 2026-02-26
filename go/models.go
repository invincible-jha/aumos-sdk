// Copyright 2026 AumOS Enterprise
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

// Package aumos provides the official Go SDK for the AumOS Enterprise platform.
package aumos

import "time"

// AgentStatus represents the lifecycle state of an agent.
type AgentStatus string

const (
	AgentStatusActive   AgentStatus = "active"
	AgentStatusInactive AgentStatus = "inactive"
	AgentStatusArchived AgentStatus = "archived"
	AgentStatusError    AgentStatus = "error"
)

// RunStatus represents the execution state of a run.
type RunStatus string

const (
	RunStatusQueued    RunStatus = "queued"
	RunStatusRunning   RunStatus = "running"
	RunStatusCompleted RunStatus = "completed"
	RunStatusFailed    RunStatus = "failed"
	RunStatusCancelled RunStatus = "cancelled"
	RunStatusTimeout   RunStatus = "timeout"
)

// IsTerminal returns true if the run has reached a final state.
func (s RunStatus) IsTerminal() bool {
	switch s {
	case RunStatusCompleted, RunStatusFailed, RunStatusCancelled, RunStatusTimeout:
		return true
	}
	return false
}

// ToolType identifies the kind of tool attached to an agent.
type ToolType string

const (
	ToolTypeFunction        ToolType = "function"
	ToolTypeRetrieval       ToolType = "retrieval"
	ToolTypeCodeInterpreter ToolType = "code_interpreter"
	ToolTypeHTTP            ToolType = "http"
)

// PolicyType classifies a governance policy.
type PolicyType string

const (
	PolicyTypeContentFilter   PolicyType = "content_filter"
	PolicyTypeRateLimit       PolicyType = "rate_limit"
	PolicyTypeDataGovernance  PolicyType = "data_governance"
	PolicyTypeAccessControl   PolicyType = "access_control"
)

// AuditOutcome is the result of an audited action.
type AuditOutcome string

const (
	AuditOutcomeSuccess AuditOutcome = "success"
	AuditOutcomeFailure AuditOutcome = "failure"
	AuditOutcomeError   AuditOutcome = "error"
)

// AgentTool describes a capability available to an agent.
type AgentTool struct {
	Name        string                 `json:"name"`
	Type        ToolType               `json:"type"`
	Description string                 `json:"description,omitempty"`
	Parameters  map[string]interface{} `json:"parameters,omitempty"`
}

// TokenUsage tracks token consumption for a run.
type TokenUsage struct {
	PromptTokens     int `json:"promptTokens,omitempty"`
	CompletionTokens int `json:"completionTokens,omitempty"`
	TotalTokens      int `json:"totalTokens,omitempty"`
}

// Agent is an AI agent registered in AumOS.
type Agent struct {
	ID           string                 `json:"id"`
	TenantID     string                 `json:"tenantId"`
	Name         string                 `json:"name"`
	Description  string                 `json:"description,omitempty"`
	Status       AgentStatus            `json:"status"`
	ModelID      string                 `json:"modelId"`
	SystemPrompt string                 `json:"systemPrompt,omitempty"`
	Tools        []AgentTool            `json:"tools"`
	Metadata     map[string]interface{} `json:"metadata"`
	CreatedAt    time.Time              `json:"createdAt"`
	UpdatedAt    time.Time              `json:"updatedAt"`
}

// IsActive returns true if the agent is in active status.
func (a *Agent) IsActive() bool { return a.Status == AgentStatusActive }

// Run is a single execution of an agent.
type Run struct {
	ID          string                 `json:"id"`
	AgentID     string                 `json:"agentId"`
	TenantID    string                 `json:"tenantId"`
	Status      RunStatus              `json:"status"`
	Input       map[string]interface{} `json:"input"`
	Output      map[string]interface{} `json:"output,omitempty"`
	Error       string                 `json:"error,omitempty"`
	Usage       *TokenUsage            `json:"usage,omitempty"`
	DurationMs  int64                  `json:"durationMs,omitempty"`
	CreatedAt   time.Time              `json:"createdAt"`
	UpdatedAt   time.Time              `json:"updatedAt"`
	CompletedAt *time.Time             `json:"completedAt,omitempty"`
}

// IsTerminal returns true if this run is in a final state.
func (r *Run) IsTerminal() bool { return r.Status.IsTerminal() }

// Succeeded returns true if the run completed successfully.
func (r *Run) Succeeded() bool { return r.Status == RunStatusCompleted }

// Model represents a model available through the AumOS registry.
type Model struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Provider        string   `json:"provider"`
	Description     string   `json:"description,omitempty"`
	Capabilities    []string `json:"capabilities"`
	ContextWindow   int      `json:"contextWindow,omitempty"`
	MaxOutputTokens int      `json:"maxOutputTokens,omitempty"`
	Deprecated      bool     `json:"deprecated"`
}

// Policy is a governance policy applied to agent executions.
type Policy struct {
	ID        string                   `json:"id"`
	Name      string                   `json:"name"`
	Type      PolicyType               `json:"type"`
	Enabled   bool                     `json:"enabled"`
	Rules     []map[string]interface{} `json:"rules"`
	CreatedAt *time.Time               `json:"createdAt,omitempty"`
}

// AuditLogEntry is a single entry in the platform audit log.
type AuditLogEntry struct {
	ID           string                 `json:"id"`
	TenantID     string                 `json:"tenantId"`
	Action       string                 `json:"action"`
	ActorID      string                 `json:"actorId"`
	ResourceType string                 `json:"resourceType,omitempty"`
	ResourceID   string                 `json:"resourceId,omitempty"`
	Outcome      AuditOutcome           `json:"outcome,omitempty"`
	Metadata     map[string]interface{} `json:"metadata"`
	Timestamp    time.Time              `json:"timestamp"`
}

// HealthResponse is returned by the platform health endpoint.
type HealthResponse struct {
	Status     string            `json:"status"`
	Version    string            `json:"version"`
	Timestamp  time.Time         `json:"timestamp"`
	Components map[string]string `json:"components"`
}

// IsHealthy returns true if the platform reports a healthy status.
func (h *HealthResponse) IsHealthy() bool { return h.Status == "healthy" }

// AgentListResponse is a paginated list of agents.
type AgentListResponse struct {
	Items         []Agent `json:"items"`
	Total         int     `json:"total"`
	NextPageToken string  `json:"nextPageToken,omitempty"`
}

// RunListResponse is a paginated list of runs.
type RunListResponse struct {
	Items         []Run  `json:"items"`
	Total         int    `json:"total"`
	NextPageToken string `json:"nextPageToken,omitempty"`
}

// ModelListResponse is a list of models.
type ModelListResponse struct {
	Items         []Model `json:"items"`
	NextPageToken string  `json:"nextPageToken,omitempty"`
}

// PolicyListResponse is a list of governance policies.
type PolicyListResponse struct {
	Items []Policy `json:"items"`
}

// AuditLogListResponse is a paginated list of audit log entries.
type AuditLogListResponse struct {
	Items         []AuditLogEntry `json:"items"`
	Total         int             `json:"total"`
	NextPageToken string          `json:"nextPageToken,omitempty"`
}

// CreateAgentRequest is the request body for creating an agent.
type CreateAgentRequest struct {
	Name         string                 `json:"name"`
	ModelID      string                 `json:"modelId"`
	Description  string                 `json:"description,omitempty"`
	SystemPrompt string                 `json:"systemPrompt,omitempty"`
	Tools        []AgentTool            `json:"tools,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// UpdateAgentRequest is the request body for partially updating an agent.
type UpdateAgentRequest struct {
	Name         *string     `json:"name,omitempty"`
	Description  *string     `json:"description,omitempty"`
	Status       *AgentStatus `json:"status,omitempty"`
	SystemPrompt *string     `json:"systemPrompt,omitempty"`
	Tools        []AgentTool `json:"tools,omitempty"`
}

// CreateRunRequest is the request body for starting a run.
type CreateRunRequest struct {
	Input          map[string]interface{} `json:"input"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
	TimeoutSeconds int                    `json:"timeoutSeconds,omitempty"`
}

// ListAgentsOptions controls the list agents query.
type ListAgentsOptions struct {
	Status    AgentStatus
	PageSize  int
	PageToken string
}

// ListRunsOptions controls the list runs query.
type ListRunsOptions struct {
	PageSize  int
	PageToken string
}

// ListModelsOptions controls the list models query.
type ListModelsOptions struct {
	Provider  string
	PageSize  int
	PageToken string
}

// ListAuditLogsOptions controls the audit log query.
type ListAuditLogsOptions struct {
	PageSize  int
	PageToken string
	StartTime string
	EndTime   string
	Action    string
}

// APIError represents an error response from the AumOS API.
type APIError struct {
	StatusCode int
	ErrorCode  string
	Message    string
	Details    map[string]interface{}
	RequestID  string
}

func (e *APIError) Error() string {
	if e.ErrorCode != "" {
		return e.ErrorCode + ": " + e.Message
	}
	return e.Message
}
