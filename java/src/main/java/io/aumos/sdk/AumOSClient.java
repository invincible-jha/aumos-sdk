/*
 * Copyright 2026 AumOS Enterprise
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package io.aumos.sdk;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import okhttp3.*;

import java.io.IOException;
import java.lang.reflect.Type;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * AumOS Enterprise API client for Java.
 *
 * <p>Thread-safe and designed to be instantiated once and shared across your application.
 *
 * <p>Usage:
 * <pre>{@code
 * AumOSClient client = AumOSClient.builder()
 *     .apiKey(System.getenv("AUMOS_API_KEY"))
 *     .build();
 *
 * // Create an agent
 * Map<String, Object> agentReq = Map.of(
 *     "name", "support-bot",
 *     "modelId", "aumos:claude-opus-4-6",
 *     "systemPrompt", "You are a helpful assistant."
 * );
 * Map<String, Object> agent = client.agents().create(agentReq);
 *
 * // Start a run
 * Map<String, Object> runReq = Map.of(
 *     "input", Map.of("message", "Hello!")
 * );
 * Map<String, Object> run = client.agents().createRun((String) agent.get("id"), runReq);
 * }</pre>
 */
public class AumOSClient implements AutoCloseable {

    private static final String DEFAULT_BASE_URL = "https://api.aumos.io/v1";
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(30);
    private static final int DEFAULT_MAX_RETRIES = 3;
    private static final String SDK_VERSION = "1.0.0";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private final String apiKey;
    private final String baseUrl;
    private final int maxRetries;
    private final OkHttpClient httpClient;
    private final Gson gson;

    private final AgentsResource agents;
    private final RunsResource runs;
    private final ModelsResource models;
    private final GovernanceResource governance;

    private AumOSClient(Builder builder) {
        String key = builder.apiKey != null ? builder.apiKey : System.getenv("AUMOS_API_KEY");
        if (key == null || key.isBlank()) {
            throw new AumOSConfigurationException(
                "No API key configured. Call Builder.apiKey() or set AUMOS_API_KEY."
            );
        }
        this.apiKey = key;
        this.baseUrl = builder.baseUrl != null ? builder.baseUrl.replaceAll("/$", "") : DEFAULT_BASE_URL;
        this.maxRetries = builder.maxRetries;

        Duration timeout = builder.timeout != null ? builder.timeout : DEFAULT_TIMEOUT;
        this.httpClient = new OkHttpClient.Builder()
            .connectTimeout(timeout)
            .readTimeout(timeout)
            .writeTimeout(timeout)
            .build();

        this.gson = new GsonBuilder()
            .setDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
            .create();

        this.agents = new AgentsResource(this);
        this.runs = new RunsResource(this);
        this.models = new ModelsResource(this);
        this.governance = new GovernanceResource(this);
    }

    public static Builder builder() {
        return new Builder();
    }

    /** Returns the agents resource for agent CRUD and run operations. */
    public AgentsResource agents() { return agents; }

    /** Returns the runs resource for fetching run status. */
    public RunsResource runs() { return runs; }

    /** Returns the models resource for querying the model registry. */
    public ModelsResource models() { return models; }

    /** Returns the governance resource for policies and audit logs. */
    public GovernanceResource governance() { return governance; }

    /**
     * Checks platform health. Does not require authentication.
     *
     * @return Health response map
     * @throws AumOSAPIException on API error
     * @throws AumOSNetworkException on network error
     */
    public Map<String, Object> health() {
        return doRequest("GET", "/health", null, false);
    }

    @SuppressWarnings("unchecked")
    Map<String, Object> doRequest(String method, String path, Object body, boolean authenticated) {
        Exception lastException = null;

        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            if (attempt > 0) {
                long backoffMs = Math.min((long) Math.pow(2, attempt - 1) * 1000L, 30_000L);
                try {
                    Thread.sleep(backoffMs);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new AumOSNetworkException("Interrupted during retry backoff", ie);
                }
            }

            try {
                Request.Builder reqBuilder = new Request.Builder()
                    .url(baseUrl + path)
                    .header("Content-Type", "application/json")
                    .header("Accept", "application/json")
                    .header("User-Agent", "aumos-java-sdk/" + SDK_VERSION);

                if (authenticated) {
                    reqBuilder.header("X-API-Key", apiKey);
                }

                RequestBody requestBody = null;
                if (body != null) {
                    requestBody = RequestBody.create(gson.toJson(body), JSON);
                } else if ("POST".equals(method) || "PATCH".equals(method) || "PUT".equals(method)) {
                    requestBody = RequestBody.create("", JSON);
                }

                switch (method) {
                    case "GET" -> reqBuilder.get();
                    case "POST" -> reqBuilder.post(requestBody);
                    case "PATCH" -> reqBuilder.patch(requestBody);
                    case "DELETE" -> reqBuilder.delete();
                    default -> throw new IllegalArgumentException("Unsupported method: " + method);
                }

                try (Response response = httpClient.newCall(reqBuilder.build()).execute()) {
                    String requestId = response.header("X-Request-ID");
                    ResponseBody responseBody = response.body();
                    String responseJson = responseBody != null ? responseBody.string() : "{}";

                    if (response.isSuccessful()) {
                        if (response.code() == 204 || responseJson.isBlank()) {
                            return Collections.emptyMap();
                        }
                        Type mapType = new TypeToken<Map<String, Object>>() {}.getType();
                        return gson.fromJson(responseJson, mapType);
                    }

                    // Parse error
                    Map<String, Object> errorBody;
                    try {
                        Type mapType = new TypeToken<Map<String, Object>>() {}.getType();
                        errorBody = gson.fromJson(responseJson, mapType);
                    } catch (Exception e) {
                        errorBody = Collections.emptyMap();
                    }

                    String message = (String) errorBody.getOrDefault("message", response.message());
                    String errorCode = (String) errorBody.get("error");

                    int status = response.code();
                    AumOSAPIException apiEx = new AumOSAPIException(message, status, errorCode, requestId);

                    if (status == 401 || status == 403 || status == 404 || status == 422) {
                        throw apiEx;
                    }
                    if (status == 429 || status >= 500) {
                        lastException = apiEx;
                        continue;
                    }
                    throw apiEx;
                }
            } catch (IOException e) {
                lastException = new AumOSNetworkException("Network error: " + e.getMessage(), e);
            }
        }

        if (lastException instanceof AumOSAPIException apiException) {
            throw apiException;
        }
        throw new AumOSNetworkException(
            "Request failed after " + maxRetries + " retries",
            lastException
        );
    }

    @Override
    public void close() {
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
    }

    // -----------------------------------------------------------------------
    // Builder
    // -----------------------------------------------------------------------

    public static final class Builder {
        private String apiKey;
        private String baseUrl;
        private Duration timeout;
        private int maxRetries = DEFAULT_MAX_RETRIES;

        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }

        public Builder baseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
            return this;
        }

        public Builder timeout(Duration timeout) {
            this.timeout = timeout;
            return this;
        }

        public Builder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        public AumOSClient build() {
            return new AumOSClient(this);
        }
    }

    // -----------------------------------------------------------------------
    // Resource classes
    // -----------------------------------------------------------------------

    /**
     * Agent operations.
     */
    public static class AgentsResource {
        private final AumOSClient client;

        AgentsResource(AumOSClient client) {
            this.client = client;
        }

        public Map<String, Object> list() {
            return client.doRequest("GET", "/agents", null, true);
        }

        public Map<String, Object> list(Map<String, String> queryParams) {
            StringBuilder path = new StringBuilder("/agents?");
            queryParams.forEach((k, v) -> path.append(k).append("=").append(v).append("&"));
            return client.doRequest("GET", path.toString(), null, true);
        }

        public Map<String, Object> create(Map<String, Object> request) {
            return client.doRequest("POST", "/agents", request, true);
        }

        public Map<String, Object> get(String agentId) {
            return client.doRequest("GET", "/agents/" + agentId, null, true);
        }

        public Map<String, Object> update(String agentId, Map<String, Object> request) {
            return client.doRequest("PATCH", "/agents/" + agentId, request, true);
        }

        public void delete(String agentId) {
            client.doRequest("DELETE", "/agents/" + agentId, null, true);
        }

        public Map<String, Object> createRun(String agentId, Map<String, Object> request) {
            return client.doRequest("POST", "/agents/" + agentId + "/runs", request, true);
        }

        public Map<String, Object> listRuns(String agentId) {
            return client.doRequest("GET", "/agents/" + agentId + "/runs", null, true);
        }

        /**
         * Poll a run until it reaches a terminal status.
         *
         * @param agentId Agent ID
         * @param runId Run ID
         * @param pollIntervalMs Polling interval in milliseconds
         * @param maxWaitMs Maximum total wait in milliseconds
         * @return The terminal run map
         * @throws InterruptedException if the calling thread is interrupted
         * @throws RuntimeException if the run does not complete within maxWaitMs
         */
        @SuppressWarnings("unchecked")
        public Map<String, Object> waitForRun(String agentId, String runId, long pollIntervalMs, long maxWaitMs)
                throws InterruptedException {
            Set<String> terminalStatuses = Set.of("completed", "failed", "cancelled", "timeout");
            long deadline = System.currentTimeMillis() + maxWaitMs;

            while (true) {
                Map<String, Object> run = client.runs().get(runId);
                String status = (String) run.get("status");

                if (terminalStatuses.contains(status)) {
                    return run;
                }

                if (System.currentTimeMillis() >= deadline) {
                    throw new RuntimeException(
                        "Run " + runId + " did not complete within " + maxWaitMs + "ms"
                    );
                }

                Thread.sleep(pollIntervalMs);
            }
        }
    }

    /**
     * Run query operations.
     */
    public static class RunsResource {
        private final AumOSClient client;

        RunsResource(AumOSClient client) {
            this.client = client;
        }

        public Map<String, Object> get(String runId) {
            return client.doRequest("GET", "/runs/" + runId, null, true);
        }
    }

    /**
     * Model registry operations.
     */
    public static class ModelsResource {
        private final AumOSClient client;

        ModelsResource(AumOSClient client) {
            this.client = client;
        }

        public Map<String, Object> list() {
            return client.doRequest("GET", "/models", null, true);
        }

        public Map<String, Object> get(String modelId) {
            return client.doRequest("GET", "/models/" + modelId, null, true);
        }
    }

    /**
     * Governance and audit log operations.
     */
    public static class GovernanceResource {
        private final AumOSClient client;

        GovernanceResource(AumOSClient client) {
            this.client = client;
        }

        public Map<String, Object> listPolicies() {
            return client.doRequest("GET", "/governance/policies", null, true);
        }

        public Map<String, Object> listAuditLogs() {
            return client.doRequest("GET", "/governance/audit-logs", null, true);
        }

        public Map<String, Object> listAuditLogs(Map<String, String> queryParams) {
            StringBuilder path = new StringBuilder("/governance/audit-logs?");
            queryParams.forEach((k, v) -> path.append(k).append("=").append(v).append("&"));
            return client.doRequest("GET", path.toString(), null, true);
        }
    }

    // -----------------------------------------------------------------------
    // Exception classes
    // -----------------------------------------------------------------------

    public static class AumOSConfigurationException extends RuntimeException {
        public AumOSConfigurationException(String message) {
            super(message);
        }
    }

    public static class AumOSAPIException extends RuntimeException {
        private final int statusCode;
        private final String errorCode;
        private final String requestId;

        public AumOSAPIException(String message, int statusCode, String errorCode, String requestId) {
            super(message);
            this.statusCode = statusCode;
            this.errorCode = errorCode;
            this.requestId = requestId;
        }

        public int getStatusCode() { return statusCode; }
        public String getErrorCode() { return errorCode; }
        public String getRequestId() { return requestId; }

        @Override
        public String toString() {
            return "AumOSAPIException{statusCode=" + statusCode +
                ", errorCode='" + errorCode + '\'' +
                ", message='" + getMessage() + '\'' +
                ", requestId='" + requestId + '\'' + '}';
        }
    }

    public static class AumOSNetworkException extends RuntimeException {
        public AumOSNetworkException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
