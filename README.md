<p align="center">
  <img src="https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js_15-App_Router-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/Auth0-EB5424?style=for-the-badge&logo=auth0&logoColor=white" />
  <img src="https://img.shields.io/badge/Airbyte-6666FF?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIj48cGF0aCBmaWxsPSIjZmZmIiBkPSJNMzI0Ljc2MiAyMTAuMzcyTDI4NC42MjQgMTYuOTIzYzMuNzY0LTE1LjA3IDM4LjcyNC0xNS4wNyA0Mi40OSAwTDQ5OS44NiAyMTAuMzdjMy43NjIgMTUuMDctMjEuMjggMjYuMi0zMi4yNiAxNC4wMkwzNTYuOTU2IDEwLjU3OGMtNC4wOTctNC41NS0xMC45MzMtNC41NS0xNS4wMyAwTDIzMS4yNzcgMjI0LjM5Yy0xMC45OCAxMi4xOC0zNi4wMjIgMS4wNS0zMi4yNi0xNC4wMnptLTEzNy41MjQgOTEuMjU2TDIyNy4zNzYgNDk1LjA4Yy0zLjc2NCAxNS4wNy0zOC43MjUgMTUuMDctNDIuNDkgMEwxMi4xNCAyOTUuMzhjLTMuNzYtMTUuMDcgMjEuMjg0LTI2LjIgMzIuMjYtMTQuMDJsMTEwLjY0MiAyMTMuODJjNC4wOTggNC41NCAxMC45MzIgNC41NCAxNS4wMyAwbDExMC42NDYtMjEzLjgyYzEwLjk4LTEyLjE4IDM2LjAyMy0xLjA1IDMyLjI2IDE0LjAyem03OC43NTUtMTQ1LjExNGwtMTEuOTQtMTAxLjExMmMtMi43MzYtMjMuMi0zNi4yNi0yMy4yLTM4Ljk5NiAwTDIwMy4xIDMzMS4xOGMtMS4zNyAxMS42IDIwLjUxIDIwLjIgMjYuNjcyIDkuMzg1TDM2MC41NSAyMjMuMWM0LjEtNy4xMyAyMS4xOS0xMS43IDMwLjMgMTAuMzhsNzAuMzUgMTcwLjQ5Yy03Ljc5LTEzLjIyLTMwLjA3LTMuNTctMzIuMiA0Ljg1TDMxNy43MDYgNTMyLjQ2NGMtMi43MzUgMjMuMi0zNi4yNiAyMy4yLTM4Ljk5NyAwbC0xMS45NS0xMDEuMTEyem0tMTkuOS00OC41MmwxMS45NCAxMDEuMTE0YzIuNzM4IDIzLjIgMzYuMjYyIDIzLjIgMzkuMDAgMEwzMDguOSAxODAuODJjMS4zNy0xMS42LTIwLjUyLTIwLjItMjYuNjc1LTkuMzhMMTUxLjQ0NiwyODguOXMtMjEuMiAxMS43LTMwLjMgLTEwLjM4bC03MC4zNTEtMTcwLjVjNy43OTEgMTMuMjIgMzAuMDc0IDMuNTcgMzIuMi00Ljg1TDE5NC4yOTQgLTIwLjQ2Yy0yLjczOC0yMy4yIDM2LjI2LTIzLjIgMzkuMDAgMEwyNDYuMSA4MC42NTR6Ii8+PC9zdmc+&logoColor=white" />
  <img src="https://img.shields.io/badge/Ghost-15171A?style=for-the-badge&logo=ghost&logoColor=white" />
</p>

<h1 align="center">Pager0</h1>
<h3 align="center">Autonomous Incident Response Agent &mdash; Zero to Remediation in 47 Seconds</h3>

<p align="center">
  An autonomous SRE agent that monitors infrastructure, detects anomalies, diagnoses root cause, calls the on-call engineer via an AI phone call, and publishes tiered incident reports &mdash; all without human intervention.
</p>

<p align="center">
  <a href="#"><strong>Submission for Deep Agents Hackathon | San Francisco, March 2026</strong></a>
</p>

---

## The Problem

**Incident response is chaotic, stressful, and slow.** When a critical service goes down at 3 AM:

| Pain Point | Impact |
|------------|--------|
| **Alert Fatigue** | Engineers wake up to vague alerts and spend 20+ minutes just finding the relevant dashboards and logs. |
| **Context Gathering** | Pulling data across multiple tools (metrics, logs, GitHub PRs) requires specialized knowledge under pressure. |
| **Communication Overhead** | Manually updating executives, customer success, and other engineers during a fire takes time away from fixing it. |
| **Slow MTTR** | The industry average Mean Time To Resolution (MTTR) is over 45 minutes, costing companies thousands per minute of downtime. |

**The result:** Burned-out engineers, frustrated customers, and significant revenue loss.

---

## The Solution

**Pager0** replaces the entire manual incident triage process. It acts as a Level 1 and Level 2 SRE that investigates issues the millisecond they occur, gathers all context, identifies the likely culprit, and then verbally briefs the human engineer to simply approve the fix.

### The "3 AM Incident" Story

> It's 3:00 AM. A bad PR is merged, causing the payment gateway latency to spike.
>
> Pager0 detects the anomaly. It dynamically spawns Airbyte connectors to pull fresh metrics. It queries Macroscope to analyze recent GitHub PRs and pinpoints the exact line of code causing the issue.
>
> Pager0 then **calls the on-call engineer on their phone**. 
> 
> *Voice Bot:* "Hi Nihal, this is Pager0. The payment gateway is experiencing high latency. I traced it to PR #42 merged 10 minutes ago. Would you like me to revert it?"
> *Engineer (half asleep):* "Uh, yeah, revert it."
>
> The verbal approval triggers an Auth0 CIBA flow. The code is reverted. Pager0 automatically drafts and publishes a highly technical post-mortem to the engineering blog, and a high-level summary to the executive dashboard via Ghost CMS.
>
> **Total time: 47 seconds.** The engineer goes back to sleep.

---

## Multimodal Pipeline Showcase

Pager0 orchestrates a complex web of tools to handle the full incident lifecycle autonomously:

| Role | Technology | What It Does |
|------|------------|--------------|
| **The Orchestrator** | Python (FastAPI) | The core agent loop that coordinates all other services and maintains state. |
| **Data Ingestion** | Airbyte (PyAirbyte) | *Dynamically* creates connectors based on the incident type to pull relevant telemetry, rather than relying on static pulls. |
| **Code Analysis** | Macroscope | Analyzes GitHub PRs to identify which recent code change likely caused the anomaly. |
| **LLM Gateway** | TrueFoundry | Proxies all LLM calls, dynamically escalating from cheap models (anomaly detection) to expensive models (root cause analysis) based on severity, while applying guardrails. |
| **Phone Escalation** | Bland AI | Executes an interactive, two-way voice call with the engineer, using function calling mid-conversation to query live data if the engineer asks questions. |
| **Authentication** | Auth0 | Uses Token Vault to manage all API credentials securely, and triggers a CIBA (Client Initiated Backchannel Authentication) flow approved via the phone call. |
| **Incident Reports** | Ghost CMS | Publishes tiered reports via the Admin API: a public executive summary and a members-only detailed technical post-mortem. |
| **Observability** | Overmind | Auto-instruments all LLM calls to trace the agent's decision-making process and provide prompt optimization recommendations. |

---

## Architecture

```mermaid
graph TB
    subgraph Infrastructure["Infrastructure & Monitoring"]
        MockInfra["Mock Infrastructure<br/>(Simulated Services)"]
        Airbyte["Airbyte (PyAirbyte)<br/>Dynamic Connectors"]
    end

    subgraph CoreAgent["Pager0 Core Agent (FastAPI)"]
        Detector["Anomaly Detector"]
        RCA["Root Cause Analyzer"]
        Orchestrator["Agent Orchestrator"]
    end

    subgraph Intelligence["Intelligence Layer"]
        TrueFoundry["TrueFoundry AI Gateway<br/>Model Escalation + Guardrails"]
        Macroscope["Macroscope<br/>GitHub PR Analysis"]
    end

    subgraph Escalation["Escalation & Resolution"]
        Bland["Bland AI<br/>Interactive Phone Call"]
        Auth0["Auth0<br/>CIBA Auth + Token Vault"]
    end

    subgraph Reporting["Reporting & Observability"]
        Ghost["Ghost CMS<br/>Tiered Incident Reports"]
        Overmind["Overmind<br/>LLM Tracing"]
    end

    %% Data Flow
    MockInfra -->|"Metrics"| Airbyte
    Airbyte -->|"Ingest"| Detector
    Detector -->|"Detect Anomaly"| Orchestrator
    
    Orchestrator <-->|"Query"| TrueFoundry
    TrueFoundry -.->|"Trace"| Overmind
    
    Orchestrator -->|"Investigate"| RCA
    RCA <-->|"Query PRs"| Macroscope
    
    Orchestrator -->|"Trigger Call"| Bland
    Bland <-->|"Mid-call Data Query"| Orchestrator
    Bland -->|"Verbal Approval"| Auth0
    Auth0 -->|"Authorize Fix"| Orchestrator
    
    Orchestrator -->|"Publish Exec/Eng Reports"| Ghost

    style Infrastructure fill:#1e1b4b,stroke:#4f46e5,color:#e0e7ff
    style CoreAgent fill:#0f172a,stroke:#3ecf8e,color:#e0e7ff
    style Intelligence fill:#1a1a2e,stroke:#4285F4,color:#e0e7ff
    style Escalation fill:#2d1b2e,stroke:#eb5424,color:#e0e7ff
    style Reporting fill:#1c1c1c,stroke:#a8b1ff,color:#e0e7ff
```

### Agent Handoff Flow

```mermaid
sequenceDiagram
    participant I as Infrastructure
    participant A as Pager0 Agent
    participant LLM as TrueFoundry (LLMs)
    participant M as Macroscope
    participant E as Engineer (Bland AI)
    participant G as Ghost CMS

    I->>A: Airbyte pulls anomalous metrics
    A->>LLM: Detect anomaly (Cheap Model)
    LLM-->>A: Anomaly Confirmed
    A->>M: Query recent PRs affecting service
    M-->>A: PR #42 identified as root cause
    A->>LLM: Generate RCA & briefing (Expensive Model)
    LLM-->>A: Briefing ready
    A->>E: Initiate Phone Call (Bland AI)
    E->>A: "What was the error rate?" (Function Call)
    A-->>E: "Error rate spiked to 14%."
    E->>A: "Okay, revert it."
    A->>A: CIBA Flow Approved
    A->>I: Revert PR #42
    A->>LLM: Draft Post-Mortem
    LLM-->>A: Markdown Report
    A->>G: Publish Tiered Reports
```

---

## Creative Sponsor Tool Usage

We explicitly avoided basic "checkbox" integrations. Every tool is used for an unpopular or highly creative feature:

| Tool | Basic Use (What we DIDN'T do) | Our Creative Use (What we DID) |
|---|---|---|
| **Auth0** | Slapping a login page on a dashboard | Implemented CIBA backchannel auth triggered by phone voice approval, plus using Token Vault so the agent never sees raw API keys. |
| **Airbyte** | Setting up a static daily data pull | The agent *dynamically* creates connectors on the fly based on what the incident is, pulling targeted data only when needed. |
| **Ghost** | Publishing a standard blog post | Using the Admin API to publish *tiered* incident reports: public summaries for executives, and members-only deep technical post-mortems for engineers. |
| **Bland AI** | Making a simple outbound notification call | Using Bland's pathway system with function calling, allowing the engineer to ask the bot live questions during the call before approving a fix. |
| **TrueFoundry**| Just proxying LLM calls | Implementing dynamic model escalation (using cheap models for basic parsing, escalating to expensive models for RCA) + active guardrails. |
| **Macroscope** | Just installing the GitHub app | Querying its PR reviews programmatically to identify the exact code change that caused the live infrastructure incident. |
| **Overmind** | Just adding the 2-line wrapper | Building the demo around the live optimization recommendations and tracing the agent's decision tree. |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Core Agent** | Python 3.10+, FastAPI |
| **Data Ingestion** | PyAirbyte (`airbyte`) |
| **Auth & Security** | Auth0 (`auth0-python`) |
| **Phone Voice Agent**| Bland AI |
| **Reporting** | Ghost CMS |
| **LLM Gateway** | TrueFoundry |
| **Code RCA** | Macroscope |
| **Observability** | Overmind |
| **Frontend Dashboard**| Next.js 15, React |

---

## Quick Start

### 1. Setup Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure API Keys

Fill in your `.env` file with the necessary credentials. Remember, we use Auth0 Token Vault, so the agent pulls keys securely.

```bash
AUTH0_DOMAIN=           # Auth0 tenant domain
AUTH0_CLIENT_ID=        # Auth0 application client ID
AUTH0_CLIENT_SECRET=    # Auth0 application client secret
BLAND_API_KEY=          # Bland AI API key
GHOST_URL=              # Ghost instance URL
GHOST_ADMIN_API_KEY=    # Ghost Admin API key (id:secret format)
TRUEFOUNDRY_API_KEY=    # TrueFoundry gateway API key
TRUEFOUNDRY_ENDPOINT=   # TrueFoundry gateway endpoint URL
OVERMIND_API_KEY=       # Overmind API key
ANTHROPIC_API_KEY=      # Anthropic API key (for TrueFoundry backend)
```

### 3. Run the Agent & Dashboard

Start the FastAPI backend:
```bash
uvicorn dashboard:app --reload --port 8000
```

*(Optional)* Start the Next.js frontend in a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

### 4. Trigger the Demo Incident

```bash
curl -X POST http://localhost:8000/api/trigger-incident
```

---

## License

MIT

---

<p align="center">
  <strong>Pager0</strong> &mdash; Built for the Deep Agents Hackathon in San Francisco, March 2026.
</p>
