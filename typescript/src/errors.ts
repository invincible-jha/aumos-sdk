// Copyright 2026 AumOS Enterprise
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

/**
 * AumOS SDK error hierarchy.
 *
 * All SDK errors extend AumOSError, making it simple to catch any
 * SDK-raised error with a single catch block.
 */

export class AumOSError extends Error {
  readonly requestId?: string;

  constructor(message: string, requestId?: string) {
    super(message);
    this.name = "AumOSError";
    this.requestId = requestId;
    // Maintain prototype chain in transpiled ES5 targets
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class AumOSAPIError extends AumOSError {
  readonly statusCode: number;
  readonly errorCode?: string;
  readonly details?: Record<string, unknown>;

  constructor(
    message: string,
    statusCode: number,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string
  ) {
    super(message, requestId);
    this.name = "AumOSAPIError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.details = details;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * 401 Unauthorized — invalid or missing API key.
 */
export class AumOSAuthenticationError extends AumOSAPIError {
  constructor(
    message: string,
    statusCode = 401,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string
  ) {
    super(message, statusCode, errorCode, details, requestId);
    this.name = "AumOSAuthenticationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * 403 Forbidden — valid credentials but insufficient permissions.
 */
export class AumOSPermissionError extends AumOSAPIError {
  constructor(
    message: string,
    statusCode = 403,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string
  ) {
    super(message, statusCode, errorCode, details, requestId);
    this.name = "AumOSPermissionError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * 404 Not Found — the requested resource does not exist.
 */
export class AumOSNotFoundError extends AumOSAPIError {
  constructor(
    message: string,
    statusCode = 404,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string
  ) {
    super(message, statusCode, errorCode, details, requestId);
    this.name = "AumOSNotFoundError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * 422 Unprocessable Entity — request body validation failed.
 */
export class AumOSValidationError extends AumOSAPIError {
  constructor(
    message: string,
    statusCode = 422,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string
  ) {
    super(message, statusCode, errorCode, details, requestId);
    this.name = "AumOSValidationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * 429 Too Many Requests — API rate limit exceeded.
 */
export class AumOSRateLimitError extends AumOSAPIError {
  /** Milliseconds to wait before retrying, if provided by the API. */
  readonly retryAfterMs?: number;

  constructor(
    message: string,
    statusCode = 429,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string,
    retryAfterMs?: number
  ) {
    super(message, statusCode, errorCode, details, requestId);
    this.name = "AumOSRateLimitError";
    this.retryAfterMs = retryAfterMs;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * 5xx Server Error — transient or persistent server-side failure.
 */
export class AumOSServerError extends AumOSAPIError {
  constructor(
    message: string,
    statusCode: number,
    errorCode?: string,
    details?: Record<string, unknown>,
    requestId?: string
  ) {
    super(message, statusCode, errorCode, details, requestId);
    this.name = "AumOSServerError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Request exceeded the configured timeout.
 */
export class AumOSTimeoutError extends AumOSError {
  constructor(message: string) {
    super(message);
    this.name = "AumOSTimeoutError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Unable to connect to the AumOS API (network error or wrong base URL).
 */
export class AumOSConnectionError extends AumOSError {
  constructor(message: string) {
    super(message);
    this.name = "AumOSConnectionError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}
