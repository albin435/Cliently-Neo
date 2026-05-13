# Cliently Project Constitution

> This document governs all architectural and engineering decisions made by Neo and its agents.

## Identity
- **Project:** Cliently — A freelancer management platform
- **Owner:** Albin
- **CTO:** Neo (AI Supervisory Layer)
- **Runtime:** OpenClaw (Execution Runtime)
- **Implementation:** Antigravity (Engineering Agents)

## Execution Model
```
User → Neo (Supervisor) → OpenClaw (Runtime) → Antigravity (Implementation) → Filesystem/Tools/Terminal
```
- **Neo** supervises, plans, reviews, and governs
- **OpenClaw** provides sandboxed shell, filesystem, and automation tooling
- **Antigravity** executes implementation and engineering tasks

## Stack
- **Web:** Next.js 14 (App Router), TypeScript, Prisma, Supabase, Tailwind CSS
- **Mobile:** React Native (Expo)
- **Desktop (macOS):** Tauri + Rust + Next.js
- **Desktop (Windows):** Tauri + Rust + Next.js
- **Orchestration:** Neo (FastAPI + SwiftUI)
- **Database:** PostgreSQL (Supabase), SQLite (local)
- **Auth:** Supabase Auth + Clerk (hybrid)
- **Payments:** Razorpay

## Architecture Rules
1. All API routes must use server-side role verification from the database — never from `user_metadata`.
2. Row-Level Security (RLS) must be enabled on all Supabase tables.
3. PII must be encrypted at rest using the `encryptPII` utility.
4. All destructive operations require explicit approval.
5. No mock/fallback implementations in production code.
6. Cross-platform parity: features must work on web, mobile, and desktop.

## Coding Standards
- TypeScript strict mode enabled
- ESLint + Prettier enforced
- No `any` types in production code
- Prisma schema is the source of truth for data models
- All API responses follow a consistent shape: `{ data, error, status }`

## Security Constraints
- API keys must never be committed to version control
- Token hashing must use `hashToken` from centralised utilities
- Invitation tokens must be single-use and time-limited
- Webhook handlers must verify signatures

## Anti-Patterns (Reject on sight)
- `user_metadata` for role checks
- Hardcoded locale assumptions
- Mock payment account creation in production
- Unprotected API routes
- Client-side-only data validation

## OpenClaw Runtime Policy
- OpenClaw is **manually installed and managed** by Albin
- Neo must **NEVER** install OpenClaw automatically
- Neo must **NEVER** configure OpenClaw automatically
- Neo must **NEVER** initialise Docker automatically
- Neo must **NEVER** modify runtime infrastructure automatically
- Neo **may** connect to OpenClaw and validate runtime health
- Neo **may** communicate with OpenClaw runtime APIs
- Neo **may** dispatch approved execution tasks to OpenClaw
- OpenClaw provides sandboxed, isolated execution — never on the personal system
- All OpenClaw execution is gated by Neo's approval workflow
