// Copyright 2026 AumOS Enterprise
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

/**
 * @packageDocumentation
 * AumOS Enterprise TypeScript SDK
 *
 * @example
 * ```typescript
 * import { AumOSClient } from "@aumos/sdk";
 *
 * const client = new AumOSClient({ apiKey: process.env.AUMOS_API_KEY });
 *
 * const agent = await client.agents.create({
 *   name: "my-agent",
 *   modelId: "aumos:claude-opus-4-6",
 * });
 * ```
 */

// Client and resource classes
export { AumOSClient, AgentsResource, RunsResource, ModelsResource, GovernanceResource } from "./client.js";

// Error hierarchy
export {
  AumOSError,
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

// All types
export type {
  // Enumerations
  AgentStatus,
  AuditOutcome,
  ModelCapability,
  PolicyType,
  RunStatus,
  ToolType,
  // Primitives
  ISODateTime,
  UUID,
  // Component types
  AgentTool,
  TokenUsage,
  // Resource types
  Agent,
  AuditLogEntry,
  HealthResponse,
  Model,
  Policy,
  Run,
  // List responses
  AgentListResponse,
  AuditLogListResponse,
  ModelListResponse,
  PaginatedResponse,
  PolicyListResponse,
  RunListResponse,
  // Request types
  CreateAgentRequest,
  CreateRunRequest,
  UpdateAgentRequest,
  // Options
  AumOSClientOptions,
  ListAgentsOptions,
  ListAuditLogsOptions,
  ListModelsOptions,
  PaginationOptions,
  WaitForRunOptions,
} from "./types.js";
