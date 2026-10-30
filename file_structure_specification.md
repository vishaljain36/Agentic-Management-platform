# 📁 AGENTIC WORKSPACE FILE STRUCTURE SPECIFICATION

This document outlines the complete repository structure for the monorepo architecture. Feed this directly to Antigravity IDE during initial setup.

```
agentic-workspace-platform/
│
├── .github/                        # CI/CD Workflows
│   └── workflows/
│       ├── deploy-frontend.yml
│       └── deploy-backend.yml
│
├── apps/
│   ├── web/                        # Next.js 15 Frontend Application
│   │   ├── app/
│   │   │   ├── (auth)/             # Authentication routes
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── signup/page.tsx
│   │   │   ├── (dashboard)/        # Tenant Workspace
│   │   │   │   ├── layout.tsx
│   │   │   │   └── workspace/
│   │   │   │       └── [id]/
│   │   │   │           ├── canvas/page.tsx     # React Flow Interactive Canvas
│   │   │   │           ├── docs/page.tsx       # Knowledge Vault / RAG
│   │   │   │           ├── logs/page.tsx       # Execution Tracing Logs
│   │   │   │           └── settings/page.tsx   # Workspace Billing & Keys
│   │   │   ├── admin/              # Super Admin Management Dashboard
│   │   │   │   ├── providers/page.tsx
│   │   │   │   ├── metrics/page.tsx
│   │   │   │   └── users/page.tsx
│   │   │   ├── api/                # Next.js Server Actions & Webhooks
│   │   │   │   └── webhooks/
│   │   │   │       ├── stripe/route.ts
│   │   │   │       └── lago/route.ts
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Landing Page
│   │   │   └── providers.tsx       # React Query, Theme & Auth Providers
│   │   │
│   │   ├── components/
│   │   │   ├── canvas/             # Spatial Canvas Components
│   │   │   │   ├── agent-node.tsx  # Custom Agent Node with Status Indicators
│   │   │   │   ├── tool-node.tsx   # Custom Tool Execution Node
│   │   │   │   ├── edge-pulse.tsx  # Animated Data Pulse Connecting Edge
│   │   │   │   └── hitl-modal.tsx  # Human-in-the-Loop Interruption Popup
│   │   │   ├── chat/               # Live SSE Streaming Components
│   │   │   │   ├── stream-chat.tsx
│   │   │   │   └── thought-tree.tsx
│   │   │   ├── ui/                 # Cyber-Glass Modified UI Primitives
│   │   │   │   ├── button.tsx
│   │   │   │   ├── glass-card.tsx
│   │   │   │   └── modal.tsx
│   │   │   └── sandbox/            # Live Embedded Terminal Component
│   │   │       └── terminal.tsx
│   │   │
│   │   ├── lib/                    # Frontend Utilities
│   │   │   ├── api-client.ts       # Axios/Fetch Wrappers for Backend API
│   │   │   └── utils.ts
│   │   │
│   │   ├── store/                  # Zustand Global State
│   │   │   ├── use-canvas-store.ts # Canvas Nodes & Graph State
│   │   │   └── use-agent-store.ts  # Execution Streams & HITL State
│   │   │
│   │   ├── tailwind.config.ts      # Cyber-Glass Theme Tokens
│   │   └── package.json
│   │
│   └── agent-backend/              # Python FastAPI Core Microservice
│       ├── app/
│       │   ├── api/
│       │   │   ├── v1/
│       │   │   │   ├── agents.py   # Agent CRUD & Execution Endpoints
│       │   │   │   ├── workflow.py # LangGraph Execution & SSE Streams
│       │   │   │   ├── RAG.py      # Vector Indexing & Document Processing
│       │   │   │   └── billing.py  # Usage Tracking Hooks
│       │   │   └── router.py
│       │   │
│       │   ├── core/
│       │   │   ├── config.py       # Pydantic Settings
│       │   │   ├── security.py     # Auth Tokens & API Key Hashing
│       │   │   ├── db.py           # PostgreSQL Connection
│       │   │   └── redis.py        # Redis Task Queue & Token Meter
│       │   │
│       │   ├── agents/             # LangGraph Orchestrations
│       │   │   ├── graphs/
│       │   │   │   ├── multi_agent_flow.py
│       │   │   │   └── hitl_graph.py
│       │   │   ├── state.py        # State Type Definitions
│       │   │   └── tools/          # Tool Wrappers
│       │   │       ├── web_search.py
│       │   │       ├── code_runner.py
│       │   │       └── sql_runner.py
│       │   │
│       │   ├── memory/             # Vector Store Interactions
│       │   │   └── qdrant_client.py
│       │   │
│       │   └── workers/            # Celery Async Execution Workers
│       │       ├── celery_app.py
│       │       └── tasks.py
│       │
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── main.py                 # FastAPI Application Entry
│
├── packages/
│   └── db/                         # Shared Database Package
│       ├── prisma/
│       │   └── schema.prisma
│       ├── index.ts
│       └── package.json
│
├── docker-compose.yml              # Dev Infrastructure (Postgres, Redis, Qdrant)
├── .env.example
├── pnpm-workspace.yaml
└── package.json
```