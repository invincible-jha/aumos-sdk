// Copyright 2026 AumOS Enterprise
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

/**
 * AumOS TypeScript SDK — HTTP client implementation.
 *
 * @example
 * ```typescript
 * import { AumOSClient } from "@aumos/sdk";
 *
 * const client = new AumOSClient({ apiKey: "sk-aumos-..." });
 *
 * const agent = await client.agents.create({
 *   name: "support-bot",
 *   modelId: "aumos:claude-opus-4-6",
 *   systemPrompt: "You are a helpful assistant.",
 * });
 *
 * const run = await client.agents.createRun(agent.id, {
 *   input: { message: "Hello!" },
 * });
 *
 * const completed = await client.agents.waitForRun(agent.id, run.id);
 * console.log(completed.output);
 * ```
 */

import {
  Agent,
  AgentListResponse,
  AgentTool,
  AuditLogListResponse,
  AumOSClientOptions,
  CreateAgentRequest,
  CreateRunRequest,
  HealthResponse,
  ListAgentsOptions,
  ListAuditLogsOptions,
  ListModelsOptions,
  Model,
  ModelListResponse,
  PaginationOptions,
  PolicyListResponse,
  Run,
  RunListResponse,
  UpdateAgentRequest,
  UUID,
  WaitForRunOptions,
} from "./types.js";
import {
  AumOSAPIError,
  AumOSAuthenticationError,
  AumOSConnectionError,
  AumOSNotFoundError,
  AumOSPermissionError,
  AumOSRateLimitError,
  AumOSServerError,
  AumOSTimeoutError,
  AumOSValidationError,
} from "./errors.js";

const DEFAULT_BASE_URL = "https://api.aumos.io/v1";
const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_MAX_RETRIES = 3;
const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function resolveApiKey(options: AumOSClientOptions): string {
  const key = options.apiKey ?? (typeof process !== "undefined" ? process.env["AUMOS_API_KEY"] : undefined);
  if (!key) {
    throw new Error(
      "No API key provided. Pass apiKey in options or set the AUMOS_API_KEY environment variable."
    );
  }
  return key;
}

// ---------------------------------------------------------------------------
// Resource classes
// ---------------------------------------------------------------------------

export class AgentsResource {
  constructor(private readonly client: AumOSClient) {}

  /**
   * List agents in the current tenant.
   */
  async list(options: ListAgentsOptions = {}): Promise<AgentListResponse> {
    const params = new URLSearchParams();
    if (options.pageSize !== undefined) params.set("pageSize", String(options.pageSize));
    if (options.pageToken) params.set("pageToken", options.pageToken);
    if (options.status) params.set("status", options.status);

    return this.client.request<AgentListResponse>("GET", `/agents?${params}`);
  }

  /**
   * Create a new agent.
   */
  async create(request: CreateAgentRequest): Promise<Agent> {
    return this.client.request<Agent>("POST", "/agents", request);
  }

  /**
   * Get a single agent by ID.
   */
  async get(agentId: UUID | string): Promise<Agent> {
    return this.client.request<Agent>("GET", `/agents/${agentId}`);
  }

  /**
   * Partially update an agent. Only provided fields are modified.
   */
  async update(agentId: UUID | string, request: UpdateAgentRequest): Promise<Agent> {
    return this.client.request<Agent>("PATCH", `/agents/${agentId}`, request);
  }

  /**
   * Delete an agent (soft delete — archived for 30 days).
   */
  async delete(agentId: UUID | string): Promise<void> {
    await this.client.request<void>("DELETE", `/agents/${agentId}`);
  }

  /**
   * Start a new run for an agent.
   */
  async createRun(agentId: UUID | string, request: CreateRunRequest): Promise<Run> {
    return this.client.request<Run>("POST", `/agents/${agentId}/runs`, request);
  }

  /**
   * List runs for a specific agent.
   */
  async listRuns(agentId: UUID | string, options: PaginationOptions = {}): Promise<RunListResponse> {
    const params = new URLSearchParams();
    if (options.pageSize !== undefined) params.set("pageSize", String(options.pageSize));
    if (options.pageToken) params.set("pageToken", options.pageToken);

    return this.client.request<RunListResponse>("GET", `/agents/${agentId}/runs?${params}`);
  }

  /**
   * Poll a run until it reaches a terminal status.
   *
   * @throws {AumOSTimeoutError} If the run does not complete within maxWaitMs.
   */
  async waitForRun(
    agentId: UUID | string,
    runId: UUID | string,
    options: WaitForRunOptions = {}
  ): Promise<Run> {
    const pollIntervalMs = options.pollIntervalMs ?? 2_000;
    const maxWaitMs = options.maxWaitMs ?? 300_000;
    const deadline = Date.now() + maxWaitMs;

    const terminalStatuses = new Set(["completed", "failed", "cancelled", "timeout"]);

    while (Date.now() < deadline) {
      const run = await this.client.runs.get(runId);
      if (terminalStatuses.has(run.status)) {
        return run;
      }
      await sleep(pollIntervalMs);
    }

    throw new AumOSTimeoutError(
      `Run ${runId} did not reach a terminal status within ${maxWaitMs}ms.`
    );
  }
}

export class RunsResource {
  constructor(private readonly client: AumOSClient) {}

  /** Retrieve a run by ID. */
  async get(runId: UUID | string): Promise<Run> {
    return this.client.request<Run>("GET", `/runs/${runId}`);
  }
}

export class ModelsResource {
  constructor(private readonly client: AumOSClient) {}

  /** List models available to the tenant. */
  async list(options: ListModelsOptions = {}): Promise<ModelListResponse> {
    const params = new URLSearchParams();
    if (options.pageSize !== undefined) params.set("pageSize", String(options.pageSize));
    if (options.pageToken) params.set("pageToken", options.pageToken);
    if (options.provider) params.set("provider", options.provider);

    return this.client.request<ModelListResponse>("GET", `/models?${params}`);
  }

  /** Get a specific model by ID. */
  async get(modelId: string): Promise<Model> {
    return this.client.request<Model>("GET", `/models/${modelId}`);
  }
}

export class GovernanceResource {
  constructor(private readonly client: AumOSClient) {}

  /** List all governance policies for the tenant. */
  async listPolicies(): Promise<PolicyListResponse> {
    return this.client.request<PolicyListResponse>("GET", "/governance/policies");
  }

  /** Retrieve audit log entries with optional filters. */
  async listAuditLogs(options: ListAuditLogsOptions = {}): Promise<AuditLogListResponse> {
    const params = new URLSearchParams();
    if (options.pageSize !== undefined) params.set("pageSize", String(options.pageSize));
    if (options.pageToken) params.set("pageToken", options.pageToken);
    if (options.startTime) params.set("startTime", options.startTime);
    if (options.endTime) params.set("endTime", options.endTime);
    if (options.action) params.set("action", options.action);

    return this.client.request<AuditLogListResponse>("GET", `/governance/audit-logs?${params}`);
  }
}

// ---------------------------------------------------------------------------
// Main client
// ---------------------------------------------------------------------------

/**
 * AumOS Enterprise API client for TypeScript/JavaScript.
 *
 * Supports Node.js 18+ and modern browser environments via the native Fetch API.
 * All methods return Promises and handle authentication, retries, and error
 * mapping automatically.
 */
export class AumOSClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;

  readonly agents: AgentsResource;
  readonly runs: RunsResource;
  readonly models: ModelsResource;
  readonly governance: GovernanceResource;

  constructor(options: AumOSClientOptions = {}) {
    this.apiKey = resolveApiKey(options);
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;

    this.agents = new AgentsResource(this);
    this.runs = new RunsResource(this);
    this.models = new ModelsResource(this);
    this.governance = new GovernanceResource(this);
  }

  /** Check platform health (no authentication required). */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("GET", "/health", undefined, false);
  }

  /**
   * Execute an HTTP request with retry logic and structured error mapping.
   *
   * @internal — use resource methods instead of calling this directly.
   */
  async request<T>(
    method: string,
    path: string,
    body?: unknown,
    authenticated = true
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "User-Agent": "aumos-typescript-sdk/1.0.0",
    };

    if (authenticated) {
      headers["X-API-Key"] = this.apiKey;
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      if (attempt > 0) {
        const backoffMs = Math.min(2 ** (attempt - 1) * 1000, 30_000);
        await sleep(backoffMs);
      }

      const controller = new AbortController();
      const timeoutHandle = setTimeout(() => controller.abort(), this.timeoutMs);

      let response: Response;
      try {
        response = await fetch(url, {
          method,
          headers,
          body: body !== undefined ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });
      } catch (fetchError: unknown) {
        clearTimeout(timeoutHandle);
        if (fetchError instanceof Error && fetchError.name === "AbortError") {
          lastError = new AumOSTimeoutError(
            `Request timed out after ${this.timeoutMs}ms: ${method} ${path}`
          );
          continue;
        }
        throw new AumOSConnectionError(
          `Network error during ${method} ${path}: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`
        );
      } finally {
        clearTimeout(timeoutHandle);
      }

      const requestId = response.headers.get("X-Request-ID") ?? undefined;

      if (response.ok) {
        if (response.status === 204 || method === "DELETE") {
          return undefined as unknown as T;
        }
        return response.json() as Promise<T>;
      }

      // Parse error body
      let errorBody: { message?: string; error?: string; details?: Record<string, unknown> } = {};
      try {
        errorBody = await response.json();
      } catch {
        // Response body may not be JSON
      }

      const message = errorBody.message ?? response.statusText;
      const errorCode = errorBody.error;
      const details = errorBody.details;
      const status = response.status;

      if (status === 401) {
        throw new AumOSAuthenticationError(message, status, errorCode, details, requestId);
      }
      if (status === 403) {
        throw new AumOSPermissionError(message, status, errorCode, details, requestId);
      }
      if (status === 404) {
        throw new AumOSNotFoundError(message, status, errorCode, details, requestId);
      }
      if (status === 422) {
        throw new AumOSValidationError(message, status, errorCode, details, requestId);
      }
      if (status === 429) {
        const retryAfterHeader = response.headers.get("Retry-After");
        const retryAfterMs = retryAfterHeader ? parseFloat(retryAfterHeader) * 1000 : undefined;

        lastError = new AumOSRateLimitError(message, status, errorCode, details, requestId, retryAfterMs);
        if (attempt < this.maxRetries) {
          await sleep(retryAfterMs ?? 2 ** attempt * 1000);
          continue;
        }
        throw lastError;
      }
      if (status >= 500) {
        lastError = new AumOSServerError(message, status, errorCode, details, requestId);
        continue;
      }

      throw new AumOSAPIError(message, status, errorCode, details, requestId);
    }

    throw lastError ?? new AumOSAPIError(`Request failed after ${this.maxRetries} retries`, 0);
  }
}
