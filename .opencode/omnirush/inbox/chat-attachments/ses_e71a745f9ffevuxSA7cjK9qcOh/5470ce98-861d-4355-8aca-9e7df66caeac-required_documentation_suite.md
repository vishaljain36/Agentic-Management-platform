# 📚 REQUIRED TECHNICAL DOCUMENTATION SUITE

This checklist outlines the technical documentation required for building, running, and maintaining the platform in **Antigravity IDE**.

---

## 1. DOCUMENTATION INVENTORY & STATUS

- [x] **Product Requirements Document (PRD)** -> Defined in `prd_document.md`
- [x] **File Structure Specification** -> Defined in `file_structure_spec.md`
- [x] **Master Blueprint & Database Schema** -> Defined in `agentic_workspace_blueprint.md`
- [ ] **API & SSE Streaming Specification** -> *See Section 2 below*
- [ ] **Environment & Security Config Guide** -> *See Section 3 below*
- [ ] **Antigravity Execution Directives** -> *See Section 4 below*

---

## 2. API & SSE STREAMING PROTOCOL SPECIFICATION

### Server-Sent Events (SSE) Endpoint for Streaming Runs
* **Endpoint:** `GET /api/v1/workflow/stream/{run_id}`
* **Headers:** 
  * `Authorization: Bearer <JWT_TOKEN>`
  * `Accept: text/event-stream`

#### Stream Event Types
1. **`node_start`**: Fired when execution enters a new agent node.
   ```json
   { "event": "node_start", "node": "researcher_agent", "timestamp": "2026-10-29T12:00:00Z" }
   ```
2. **`token_delta`**: Real-time token generation stream from the LLM.
   ```json
   { "event": "token_delta", "delta": "Analyzing market data...", "node": "researcher_agent" }
   ```
3. **`hitl_interrupt`**: Fired when execution pauses for human approval.
   ```json
   { 
     "event": "hitl_interrupt", 
     "required_action": "EXECUTE_PYTHON_CODE", 
     "payload": { "code": "import os; print(os.listdir())" } 
   }
   ```
4. **`run_complete`**: Workflow finished successfully.
   ```json
   { "event": "run_complete", "total_tokens": 1420, "cost_usd": 0.012 }
   ```

---

## 3. ENVIRONMENT & SECURITY CONFIGURATION (`.env.example`)

```env
# APP GENERAL
NODE_ENV=development
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000

# DATABASE & CACHE
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/agentic_workspace?schema=public"
REDIS_URL="redis://localhost:6379/0"

# VECTOR DATABASE
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY="your-qdrant-api-key"

# LLM PROVIDER KEYS (API GATEWAY)
OPENAI_API_KEY="sk-proj-..."
ANTHROPIC_API_KEY="sk-ant-..."
GOOGLE_GEMINI_API_KEY="AIzaSy..."

# PAYMENT & METERING
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
LAGO_API_KEY="lago_..."

# CODE SANDBOXING
E2B_API_KEY="e2b_..."
```

---

## 4. ANTIGRAVITY IDE EXECUTION PROMPT DIRECTIVES

Copy and paste these exact instruction sequences into Antigravity IDE step-by-step:

### Step 1: Initialize Monorepo & Dependencies
> *"Set up a monorepo structure matching `file_structure_spec.md`. Configure pnpm workspaces for `apps/web` (Next.js 15 App Router with Tailwind CSS) and `apps/agent-backend` (FastAPI). Install `@xyflow/react`, `zustand`, `lucide-react`, and `@prisma/client` in the web application."*

### Step 2: Database & Prisma Client Migration
> *"Load `agentic_workspace_blueprint.md` for the database schema. Place the schema inside `packages/db/prisma/schema.prisma`. Initialize Docker Compose with PostgreSQL, Redis, and Qdrant containers, and execute `npx prisma db push` to generate database tables."*

### Step 3: Implement Python FastAPI & LangGraph State Machine
> *"Build the FastAPI backend structure inside `apps/agent-backend`. Implement the LangGraph execution flow with state graphs from `agentic_workspace_blueprint.md`. Set up the SSE endpoint (`GET /api/v1/workflow/stream/{run_id}`) following the format in `required_docs_checklist.md`."*

### Step 4: Build Cyber-Glass Frontend & Spatial Canvas
> *"Inside `apps/web/app/(dashboard)/workspace/[id]/canvas/page.tsx`, build the infinite canvas using React Flow (`@xyflow/react`). Apply the dark Cyber-Glass visual theme defined in `agentic_workspace_blueprint.md`. Bind the node graph state to a Zustand store (`use-canvas-store.ts`) and add live SSE token rendering."*