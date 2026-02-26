// Copyright 2026 AumOS Enterprise
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

/**
 * TypeScript type definitions for the AumOS Enterprise API.
 *
 * All types are auto-generated from the OpenAPI spec and then refined
 * with stricter TypeScript typing (branded UUIDs, discriminated unions, etc.)
 */

// ---------------------------------------------------------------------------
// Primitive utilities
// ---------------------------------------------------------------------------

/** A string that represents a UUID v4. */
export type UUID = string & { readonly _brand: "UUID" };

/** ISO-8601 date-time string. */
export type ISODateTime = string & { readonly _brand: "ISODateTime" };

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type AgentStatus = "active" | "inactive" | "archived" | "error";

export type RunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "timeout";

export type ToolType =
  | "function"
  | "retrieval"
  | "code_interpreter"
  | "http";

export type PolicyType =
  | "content_filter"
  | "rate_limit"
  | "data_governance"
  | "access_control";

export type AuditOutcome = "success" | "failure" | "error";

export type ModelCapability =
  | "text"
  | "vision"
  | "function_calling"
  | "structured_output"
  | "streaming";

// ---------------------------------------------------------------------------
// Shared component types
// ---------------------------------------------------------------------------

export interface AgentTool {
  name: string;
  type: ToolType;
  description?: string;
  parameters?: Record<string, unknown>;
}

export interface TokenUsage {
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
}

// ---------------------------------------------------------------------------
// Core resource types
// ---------------------------------------------------------------------------

export interface Agent {
  id: UUID;
  tenantId: UUID;
  name: string;
  description?: string;
  status: AgentStatus;
  modelId: string;
  systemPrompt?: string;
  tools: AgentTool[];
  metadata: Record<string, unknown>;
  createdAt: ISODateTime;
  updatedAt: ISODateTime;
}

export interface Run {
  id: UUID;
  agentId: UUID;
  tenantId: UUID;
  status: RunStatus;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  usage?: TokenUsage;
  durationMs?: number;
  createdAt: ISODateTime;
  updatedAt: ISODateTime;
  completedAt?: ISODateTime;
}

export interface Model {
  id: string;
  name: string;
  provider: string;
  description?: string;
  capabilities: ModelCapability[];
  contextWindow?: number;
  maxOutputTokens?: number;
  deprecated: boolean;
}

export interface Policy {
  id: UUID;
  name: string;
  type: PolicyType;
  enabled: boolean;
  rules: Array<Record<string, unknown>>;
  createdAt?: ISODateTime;
}

export interface AuditLogEntry {
  id: UUID;
  tenantId: UUID;
  action: string;
  actorId: string;
  resourceType?: string;
  resourceId?: string;
  outcome?: AuditOutcome;
  metadata: Record<string, unknown>;
  timestamp: ISODateTime;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  timestamp: ISODateTime;
  components: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Paginated list responses
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  total?: number;
  nextPageToken?: string;
}

export type AgentListResponse = PaginatedResponse<Agent> & { total: number };
export type RunListResponse = PaginatedResponse<Run> & { total: number };
export type ModelListResponse = PaginatedResponse<Model>;
export type AuditLogListResponse = PaginatedResponse<AuditLogEntry> & { total: number };

export interface PolicyListResponse {
  items: Policy[];
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface CreateAgentRequest {
  name: string;
  modelId: string;
  description?: string;
  systemPrompt?: string;
  tools?: AgentTool[];
  metadata?: Record<string, unknown>;
}

export interface UpdateAgentRequest {
  name?: string;
  description?: string;
  status?: AgentStatus;
  systemPrompt?: string;
  tools?: AgentTool[];
  metadata?: Record<string, unknown>;
}

export interface CreateRunRequest {
  input: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  timeoutSeconds?: number;
}

// ---------------------------------------------------------------------------
// Pagination options
// ---------------------------------------------------------------------------

export interface PaginationOptions {
  pageSize?: number;
  pageToken?: string;
}

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

export interface ApiErrorBody {
  error?: string;
  message: string;
  details?: Record<string, unknown>;
  requestId?: string;
}

// ---------------------------------------------------------------------------
// Client configuration
// ---------------------------------------------------------------------------

export interface AumOSClientOptions {
  /** API key for authentication. Falls back to AUMOS_API_KEY env var. */
  apiKey?: string;
  /** Override the default API base URL. */
  baseUrl?: string;
  /** Request timeout in milliseconds. Defaults to 30000. */
  timeoutMs?: number;
  /** Maximum number of retries for transient errors. Defaults to 3. */
  maxRetries?: number;
}

export interface ListAgentsOptions extends PaginationOptions {
  status?: AgentStatus;
}

export interface ListModelsOptions extends PaginationOptions {
  provider?: string;
}

export interface ListAuditLogsOptions extends PaginationOptions {
  startTime?: string;
  endTime?: string;
  action?: string;
}

export interface WaitForRunOptions {
  /** Milliseconds between status polls. Defaults to 2000. */
  pollIntervalMs?: number;
  /** Maximum wait time in milliseconds. Defaults to 300000 (5 min). */
  maxWaitMs?: number;
}
