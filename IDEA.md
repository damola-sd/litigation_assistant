AI-Powered Litigation Prep Assistant (Kenya)

1. Problem
   What exactly is the problem?
   Litigation prep is slow and repetitive:
   Extracting facts from messy inputs
   Building timelines
   Mapping facts to legal arguments
   Drafting structured briefs
   Who has it?
   Paralegals
   Junior lawyers
   Small-to-mid law firms
   Why do current solutions fall short?
   Chat tools are manual and reactive
   No end-to-end workflow automation
   No structured outputs for litigation prep

2. Solution Overview
   What are we building?
   A multi-agent AI system that transforms raw case input into a structured legal brief.

User Flow
Input
Case facts (text input)
Optional file uploads (PDF/DOCX)

Processing (Agent Pipeline)
Extraction Agent → facts + entities + timeline
Strategy Agent → legal reasoning + applicable laws
Drafting Agent → structured legal brief
QA Agent → validation + risk checks

Output
Timeline of events
Legal reasoning
Structured legal brief:
Facts
Issues
Arguments
Counterarguments
Conclusion
QA / risk notes

What makes this different
Workflow automation (not chat)
Structured legal output (not freeform text)
Visible multi-agent reasoning pipeline

3. System Design (end-to-end thinking)

Frontend (Next.js)
Framework: Next.js
Pages / Routes
Public
/ → Landing page (marketing + pricing)
/pricing → Subscription plans (Clerk integration)
/login → Clerk auth page

Authenticated App
/dashboard
Main input screen
Create new case analysis
/dashboard/new
Case input form:
Text area (case facts)
File upload (PDF/DOCX)
/dashboard/history
List of past analyses
Filter by date/status
/dashboard/case/[id]
Full result view:
Agent step-by-step outputs
Final legal brief
QA validation notes

Frontend Components
CaseInputForm
AgentStepViewer (important for demo)
ResultPanel
HistoryTable
FileUploader

Frontend Responsibilities
Auth via Clerk
Collect user input
Call backend APIs
Render agent outputs step-by-step
Show history + subscription status

Auth + Billing
Clerk
Free trial gating
Subscription plans
Route protection middleware

Backend (FastAPI)
Framework: FastAPI

Core Responsibilities
Handle AI orchestration
Run agent pipeline
Manage RAG retrieval
Store user history
Validate Clerk JWT

API Endpoints
Auth / User
GET /me
Returns user profile (from Clerk JWT)

Core AI Flow
POST /analyze
Input:
case_text
optional files
Output:
full agent pipeline result

History
GET /history
Returns all past analyses for user
GET /history/{id}
Returns full case result + agent steps

Health
GET /health
System check

AI Layer (inside backend)
Orchestration Flow
/analyze
↓
Extraction Agent
↓
RAG Retrieval Layer
↓
Strategy Agent
↓
Drafting Agent
↓
QA Agent
↓
Return structured response

Agents

1. Extraction Agent
   Extract:
   Facts
   Entities
   Timeline

2. Strategy Agent
   Maps:
   Kenyan legal context
   Arguments
   Applicable laws

3. Drafting Agent
   Produces:
   Structured legal brief

4. QA Agent
   Validates:
   Grounding
   Missing logic
   Hallucination risk

RAG Layer
Legal dataset (Kenya Law excerpts)
Embedding + retrieval step before Strategy Agent

Storage
Postgres:
users
cases
results
Vector store:
FAISS / lightweight DB

4. Data Strategy
   Kenyan legal documents:
   Case law excerpts
   Statutes (curated subset)

RAG Pipeline
Chunk documents
Generate embeddings
Store in vector DB
Retrieve relevant context per query

5. Feasibility
   Feasibility: HIGH

Risks
Overbuilding agents
Spending too much time on data prep
Adding unnecessary frameworks

Mitigation
Start text-only (no file parsing v1)
Limit to 3–4 agents max
Use API-based LLMs
Keep dataset small and focused

6. Deployment (keep it lean)

Frontend
Vercel

Backend
Render (recommended)
Alternative: Fly.io / AWS (only if already set up)

Auth & Billing
Clerk

AI Access
External LLM APIs (no self-hosting)

Storage
Postgres
FAISS / lightweight vector store/ ChromaDB

Deployment Goal
Fast
Cheap
Minimal infra complexity

7. Impact
   Who benefits?
   Lawyers
   Paralegals
   Small firms

Value
Saves hours per case
Standardizes legal prep
Automates repetitive legal structuring
Demonstrates real multi-agent AI system design

8. Team Split
   Rithwik
   FastAPI backend architecture
   Agent orchestration
   AI integration

John
Next.js frontend (App Router)
Clerk integration (auth + billing UI)

Amit
RAG pipeline
Legal dataset ingestion + embeddings

Damola
Agent design (prompts + reasoning flow)
QA agent logic

Sodiq
Deployment (Vercel + Render)
Database setup
Logging + monitoring

9. Final Summary Table (for voting)
   Section
   Details
   Problem
   Manual litigation prep is slow and repetitive
   Solution
   Multi-agent system generating structured legal briefs
   AI Approach
   RAG + Multi-Agent (Extraction, Strategy, Drafting, QA)
   Feasibility
   High
   Key Risk
   Over-engineering agents + data prep delays
   Deployment Plan
   Next.js (Vercel) + FastAPI (Render) + Clerk + Postgres
   Team Allocation
   Clear split across FE, BE, AI, Data, Infra

Final Notes
Keep FastAPI thin (orchestration only)
Make agent outputs visible in UI (critical for demo)
Avoid unnecessary complexity
Optimize for working system + clear story
