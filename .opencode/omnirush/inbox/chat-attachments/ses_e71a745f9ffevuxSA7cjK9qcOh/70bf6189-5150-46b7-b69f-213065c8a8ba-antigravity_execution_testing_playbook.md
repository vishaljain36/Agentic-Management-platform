# 🛠️ ANTIGRAVITY IDE STEP-BY-STEP EXECUTION & TESTING PLAYBOOK

Use these exact prompts sequentially inside Antigravity IDE. Each step enforces an **Autonomous Test & Debug Loop** so the IDE verifies its own code before continuing.

---

## 🚀 PHASE 1: Monorepo Setup, Infrastructure & Prisma Database

### Prompt 1: Initial Setup & Database Layer

```text
Act as a Principal Full-Stack AI Infrastructure Engineer.

Phase Goal: Initialize the monorepo, set up docker services, and deploy the PostgreSQL database schema with Prisma.

Task Instructions:
1. Initialize a pnpm monorepo matching the file structure in `file_structure_spec.md`.
2. Create `docker-compose.yml` with PostgreSQL (port 5432), Redis (port 6379), and Qdrant Vector DB (port 6333).
3. In `packages/db`, initialize Prisma and configure `schema.prisma` using the schema provided in `agentic_workspace_blueprint.md`.
4. Create `.env.example` containing required database connection strings, Redis host, Qdrant URL, and secrets.

AUTOMATED TESTING & DEBUGGING PROTOCOL:
Execute the following verification steps. If any errors occur, analyze the logs, debug, and fix until all commands pass:
a. Run `docker compose up -d` and verify all containers are healthy.
b. Run `pnpm install` across the monorepo to verify workspace dependencies.
c. Run `pnpm --filter db exec prisma validate` to confirm schema validity.
d. Run `pnpm --filter db exec prisma db push` to verify database connection and table creation.

Do not move to Phase 2 until all tests pass with exit code 0.
```

---

## ⚡ PHASE 2: Core LangGraph Engine & FastAPI Backend

### Prompt 2: Async Orchestrator & Execution Streams

```text
Act as a Senior Python Backend & AI Framework Specialist.

Phase Goal: Build the core FastAPI microservice with LangGraph state graphs, Celery task queues, and Server-Sent Events (SSE) streaming.

Task Instructions:
1. In `apps/agent-backend`, set up a FastAPI application (`main.py`) with Pydantic configuration (`core/config.py`).
2. Implement the LangGraph execution graph (`app/agents/graphs/multi_agent_flow.py`) with a Human-In-The-Loop (HITL) interruption state as defined in `agentic_workspace_blueprint.md`.
3. Create `app/api/v1/workflow.py` with an SSE streaming endpoint (`/api/v1/workflow/stream/{run_id}`) that streams real-time token outputs and node execution states.
4. Implement Redis-backed task queuing using Celery (`app/workers/celery_app.py`).

AUTOMATED TESTING & DEBUGGING PROTOCOL:
Execute the following verification steps. Debug and resolve any failures:
a. Write a unit test suite in `apps/agent-backend/tests/test_graph.py` using PyTest to test graph state transitions and HITL pauses.
b. Run `poetry run pytest` or `pytest` inside `apps/agent-backend/` and verify 100% pass rate.
c. Execute a test curl request to the SSE endpoint to verify correct `text/event-stream` response formatting.

Confirm all tests pass before proceeding.
```

---

## 🧠 PHASE 3: Knowledge Ingestion Vault & Vector RAG Integration

### Prompt 3: Qdrant Vector Indexer & RAG Tools

```text
Act as a Data & Vector DB Specialist.

Phase Goal: Build document parsing, embedding creation, and Qdrant vector retrieval pipelines for multi-tenant workspaces.

Task Instructions:
1. Implement `apps/agent-backend/app/memory/qdrant_client.py` using `qdrant-client` and FastEmbed/OpenAI embeddings.
2. Build `apps/agent-backend/app/api/v1/rag.py` to handle uploading, chunking, and indexing of PDF, DOCX, and Text documents into workspace-isolated Qdrant collections.
3. Bind the vector search tool as a callable LangGraph tool inside `app/agents/tools/vector_search.py`.

AUTOMATED TESTING & DEBUGGING PROTOCOL:
Execute the following verification steps:
a. Run an integration test (`tests/test_rag.py`) that uploads a dummy document, creates vector embeddings, queries Qdrant, and asserts similarity score threshold > 0.75.
b. Test tenant isolation by asserting that Workspace A cannot query vector collections belonging to Workspace B.
c. Fix any memory leaks or unresolved payload serialization errors.
```

---

## 🎨 PHASE 4: Cyber-Glass Spatial Canvas UI (Next.js 15)

### Prompt 4: React Flow Canvas & Real-Time Streaming UI

```text
Act as a Frontend Lead & UI/UX Specialist.

Phase Goal: Construct the Next.js 15 Cyber-Glass Spatial Workspace frontend with React Flow and Zustand.

Task Instructions:
1. Set up Tailwind CSS theme tokens matching the "Cyber-Glass Void" palette specified in `agentic_workspace_blueprint.md`.
2. Implement `@xyflow/react` in `apps/web/app/(dashboard)/workspace/[id]/canvas/page.tsx`.
3. Create custom React Flow nodes (`agent-node.tsx`, `tool-node.tsx`) with animated edge pulses (`edge-pulse.tsx`) for dynamic data transfers.
4. Build `components/canvas/hitl-modal.tsx` to handle Human-in-the-Loop approval events emitted by the SSE stream.
5. Setup Zustand (`store/use-agent-store.ts`) to manage live stream states and spatial graph node connections.

AUTOMATED TESTING & DEBUGGING PROTOCOL:
Execute the following verification steps:
a. Run `pnpm --filter web type-check` and resolve all TypeScript strictness errors.
b. Run `pnpm --filter web build` to verify Next.js Server Component compilation without errors.
c. Run Playwright/Cypress or React Testing Library tests on the custom canvas components to verify node rendering.
```

---

## 💳 PHASE 5: Usage-Based Metering, Stripe Billing & Admin Dashboard

### Prompt 5: Financial Metrics, Metering & Admin Panel

```text
Act as a FinTech & SaaS Systems Engineer.

Phase Goal: Implement token-level usage metering with Lago/Stripe and build the Super Admin monitoring console.

Task Instructions:
1. Implement Redis token counters in `apps/agent-backend/app/core/redis.py` that record input/output token usage per run.
2. Calculate cost metrics dynamically using:
   $$\text{Total Cost} = \sum (\text{Tokens} \times \text{Rate}) + (\text{Tools} \times \text{Cost})$$
3. Create Stripe webhook handler at `apps/web/app/api/webhooks/stripe/route.ts` to sync subscriptions and update workspace credits.
4. Build Super Admin views at `apps/web/app/admin/` displaying platform margins, LLM provider fallbacks, and user management.

AUTOMATED TESTING & DEBUGGING PROTOCOL:
Execute the following verification steps:
a. Run unit tests simulating 10,000 token consumption events and assert correct Redis counter increments and budget cap interruptions.
b. Trigger mock Stripe webhook payloads using Stripe CLI (`stripe trigger invoice.paid`) and verify database updates.
c. Run full end-to-end type check and build across all monorepo packages (`pnpm build`).
```

---

## 🔒 PHASE 6: Safe Execution Sandboxes & Security Audit

### Prompt 6: Isolation & Security Verification

```text
Act as a DevSecOps Lead.

Phase Goal: Secure custom code execution tools in Docker sandboxes and perform end-to-end platform verification.

Task Instructions:
1. Implement `app/agents/tools/code_runner.py` to execute user Python code inside ephemeral Docker containers with CPU/Memory bounds ($512\text{ MB}$, max runtime $60\text{ seconds}$).
2. Implement CORS rules, Rate Limiting (FastAPI slowapi), and API Key hashing (`packages/db`).
3. Run a comprehensive automated system health-check across all services.

AUTOMATED TESTING & DEBUGGING PROTOCOL:
Execute the following verification steps:
a. Run malicious payload tests in the code sandbox (e.g., attempt host file system access or long loops) and verify successful sandbox isolation and timeout termination.
b. Run full test suites across monorepo: `pnpm test` and `pytest`.
c. Run `pnpm build` to ensure production readiness without warnings or errors.
```