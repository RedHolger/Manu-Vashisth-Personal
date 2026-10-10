# Job‑Aware LaTeX Resume Workspace: Deep Research and Build Specification

## Product definition and market context

The core idea is a **resume “workspace”** that looks and behaves like a lightweight LaTeX IDE: a project list → project editor → live PDF preview, with an AI assistant that helps tailor content to a specific job description and fixes LaTeX/lint errors. This positions the product closer to collaborative LaTeX tools (editor + compile + preview) than to traditional drag‑and‑drop resume builders. Online LaTeX platforms demonstrate sustained demand for this workflow: they emphasize frequent compilation into PDF and tight edit→preview loops, and they are used at large scale for technical documents. citeturn14search34turn14search17

On the “job tailoring” side, the value proposition aligns with the reality that many employers screen candidates via structured processes and automated tooling, especially during initial screening. For example, guidance from major job platforms explicitly recommends extracting keywords from the job listing and echoing them in the resume to improve ATS performance. citeturn9search30 Employers are also trending toward skills‑based hiring and using skills signals during screening, increasing the value of tools that can translate a job description into skills/requirements and then map those to a candidate’s evidence. citeturn9search1

A meaningful competitive set already exists for “resume ↔ job description match score / keyword gap” (e.g., products that compute a match rate and recommend edits). Jobscan markets “resume ↔ job listing” analysis and a match rate, citeturn14search3turn14search0 Teal markets matching a resume to specific job descriptions with a match score, citeturn14search1 and Rezi markets ATS checks and job‑specific tailoring features. citeturn14search4turn14search2  
Your differentiator is **format + workflow**: a “Prism‑like” IDE for LaTeX resumes, where tailoring is integrated into the editing surface (diffs, patches, compile feedback, forward/inverse navigation), rather than a separate “upload → score → export” funnel.

A key product‑risk (and trust risk) is **hallucinated or misleading resume content**. Universities that advise on generative AI for resumes emphasize responsible use (supporting drafting/editing while ensuring accuracy and integrity remains the student’s responsibility). citeturn9search2 This suggests your assistant should be designed to: (a) never invent employers, titles, dates, metrics; (b) propose changes as tracked edits; (c) require explicit user confirmation and/or evidence references per bullet.

## Job data acquisition constraints for LinkedIn, Internshala, and Naukri

Your original scope includes “use LinkedIn API, Internshala API, Naukri API to search for all listed jobs online.” The deep‑research conclusion is that **this is not realistically achievable as a compliant, scalable product** without contractual partnerships or licensed aggregators, because:

### LinkedIn

1) **Official job APIs are not “job search APIs” for general developers.** LinkedIn’s Job Posting API is oriented to posting/managing jobs via approved partners (ATS systems, job distributors), not harvesting/searching all jobs. citeturn5view3turn5view4  
2) **Access is heavily restricted.** As of February 24, 2026, the Microsoft Learn documentation for LinkedIn’s Job Posting API states they are “currently not accepting new partnerships” for that API and points prospective integrators to request access to “Apply Connect.” citeturn5view3  
3) **Self‑serve LinkedIn API eligibility criteria conflict with your reliance plan.** LinkedIn’s API Terms of Use include a self‑serve program condition that an application “DOES NOT rely on access to the APIs as a fundamental aspect of your business.” citeturn5view0turn5view1 A resume maker whose centerpiece is “pull LinkedIn jobs and tailor resumes” would likely be interpreted as relying on LinkedIn access as a fundamental aspect.  
4) **Automation/scraping prohibitions are explicit.** LinkedIn’s help guidance says they “don’t permit” crawlers/bots/extensions that scrape or automate activity on LinkedIn; it cites the User Agreement prohibition on using scripts/robots/crawlers to scrape or copy services including profiles and other data. citeturn5view2

**Implication:** A “LinkedIn jobs search” connector that programmatically enumerates listings is not a safe assumption. Many third‑party “LinkedIn jobs APIs” on scraping platforms explicitly state the data “isn’t available through any official API,” which is a strong signal these solutions are wrappers around scraping rather than sanctioned access. citeturn15view0 If you build on them, you inherit ToS and enforcement risk (bans, legal claims, churn).

### Internshala

Internshala’s Terms and Conditions contain an explicit prohibition on automated extraction/scraping/crawling/data mining of site content and also explicitly restrict using site data for developing/training/fine‑tuning AI/LLM systems without prior written consent and a separate agreement. citeturn6view0  
In addition, Internshala’s robots.txt disallows key job and internship search/detail paths for general user agents (including `/job/search/`, `/job/details/`, etc.). citeturn6view1

**Implication:** “Internshala API for job search” should be treated as **non‑existent publicly** unless you are entering a negotiated partnership. A connector that scrapes is directly in conflict with their stated terms.

### Naukri

Direct verification of Naukri.com ToS/robots constraints is limited through this browsing environment because access to naukri.com is blocked by robots.txt at the tool level (meaning I cannot reliably quote Naukri.com’s own legal pages here). citeturn3search0 However, Naukri is a major recruitment brand under entity["company","Info Edge (India) Limited","recruitment company india"]’s portfolio, and its business model depends on job listings and resume database access. citeturn1search12  
A closely related Info Edge property (Naukrigulf) explicitly prohibits scraping/downloading/extracting platform information and attempting to circumvent protections (CAPTCHAs, service limits, bot exclusions). citeturn3search20 While this is not a substitute for Naukri.com’s own terms, it’s a relevant indicator of the group’s stance toward automated extraction.

**Implication:** You should treat Naukri job harvesting as a high‑risk dependency unless you have written permission or a licensed job‑data provider.

### Legal reality check: “public scraping may be legal” ≠ “product risk is low”

In the US, litigation around scraping (hiQ v. LinkedIn) shows that **Computer Fraud and Abuse Act (CFAA) theories can be limited for purely public pages**, but platforms can still pursue **contract (ToS) claims** and other theories. citeturn7search12turn7search1turn7search25 The hiQ matter ultimately ended with LinkedIn prevailing on breach‑of‑contract grounds and a settlement including a permanent injunction against scraping. citeturn7search28turn7search32turn7search24  
Separately, privacy regulators have penalized LinkedIn‑adjacent scraping use cases (e.g., the French CNIL’s €240,000 fine against KASPR for collecting LinkedIn user contact details, including when users masked them). citeturn7search2turn7search6

**Product takeaway:** even if a narrow legal theory might be defensible in a jurisdiction, building a consumer product that depends on scraping major job boards is typically fragile (technical blocks + account bans) and risky (contract/privacy enforcement).

### Recommended scope pivot: job intake, not job harvesting

A realistic, durable scope is:

1) **Job‑specific tailoring given a job posting the user provides** (URL import, copy/paste description, or email forward from job alerts), and  
2) **Job aggregation only from sources you’re licensed/authorized to ingest**, plus “open” job feeds.

Concrete compliant job‑ingestion avenues include:
- **Company career pages with structured data**: many employers expose job detail pages with Schema.org `JobPosting` markup; Google documents required/supported properties and how job details should be provided. citeturn12search0turn12search3turn12search4  
- **RSS feeds from job boards that explicitly publish them** (example: Remotive provides a public RSS feed for remote jobs). citeturn12search5  
- **Licensed aggregators**: vendors market normalized job posting APIs across many sources (example: TheirStack markets “Naukri Job Posting API” and broader aggregation). citeturn15view2 This is not automatically “compliance solved,” but a commercial contract can shift risk from “unauthorized scraping you maintain” to “licensed feed you pay for,” which is often a better business posture.

## UI and UX specification from your Prism‑style screenshots

Your screenshots show two principal surfaces:

### Projects list surface

A dark theme “Your Projects” page with:
- Left sidebar navigation with three items: “All Projects”, “Your Projects” (selected), “Shared with you”.
- Top header row containing: page title (“Your Projects”), a search bar, view controls (list/grid toggle), an “Import” dropdown, and a prominent “+ New” button.
- Main content area: a table/list of projects with columns like Name and Created, each row having an icon thumbnail + project title, and an overflow menu at the far right.

This implies a clean information architecture:
- **Project entity**: name, createdAt, modifiedAt, lastOpenedAt, template, tags, storage location, and possibly collaboration metadata (even if you ship single‑user first).

### Editor workspace surface

The editor view resembles a LaTeX IDE:
- A left side panel with the project name (dropdown), two tabs (“Files”, “Chats”), a file list (e.g., `main.tex`, plus assets), and an “Outline” section beneath that.
- The main area is a **split view**: code editor on the left (line numbers + monospaced), PDF preview on the right with its own toolbar (page count, zoom mode, overflow menu).
- A “Tools” button appears at the top right of the editor area (distinct from PDF toolbar), implying a command palette or a tools drawer (compile, logs, settings, export).
- A bottom region shows compact status/log output (e.g., compile progress, errors, or system messages) separate from the main editor.

**Interaction model that matches this UI**
- Resizable panes: (left sidebar) | (editor) | (preview).
- “Compile” is a first‑class command with visible progress in the preview toolbar (e.g., “Initializing…”).
- When compilation fails, the logs panel should become “active” and connect errors to lines (click error → jump to editor line; and ideally forward search to preview position).
- Chat is project‑scoped (not global) and logically connected to the current file or selection.

**Implementation note:** your app should treat “Chat” as a multi‑tab tool, not a modal. If the assistant is producing edits, it should produce diffs/patches that apply to `main.tex` and show the result immediately in the preview after compile.

## Architecture and stack decisions for a TypeScript build

Your requirements (“TypeScript application,” “opens a window with a LaTeX file,” local compile) strongly suggest a desktop container—most plausibly an Electron app. Electron introduces security responsibilities, but its model fits local TeX toolchains and local file access.

### Desktop app baseline: Electron + React + local TeX toolchain

Security‑relevant defaults in Electron matter because your app will render complex content (PDF, HTML panels) and may open job descriptions from the web. Electron’s security guidance recommends strong isolation (e.g., using `contextIsolation`) and warns that enabling Node integration in the renderer disables sandboxing. citeturn4search0turn4search4turn4search20turn4search8  
This should directly influence your architecture:

- **Renderer process**: strictly UI only (React, Monaco editor, PDF preview), no direct Node APIs.
- **Preload script**: narrow, audited IPC surface.
- **Main process**: file access, spawn compile, manage AI calls, manage secrets, manage job ingestion.

### Data model and boundaries (implementation‑ready)

A minimal internal domain model that supports your UI and future connectors:

- **Project**
  - `projectId`, `name`, `createdAt`, `updatedAt`
  - `files[]` (logical file tree)
  - `settings` (engine: `pdflatex|xelatex|lualatex`, latexmk options, template id)
  - `aiPreferences` (tone, verbosity, target role, constraints)
  - `jobTargets[]` (saved job profiles)

- **JobTarget (normalized)**
  - `source` (manual paste | URL import | RSS | licensed aggregator)
  - `title`, `company`, `location`, `employmentType`, `seniority`
  - `descriptionRaw` (original text/HTML)
  - `requirements` (structured: skills, responsibilities, qualifications)
  - `keywords` (ranked)
  - `timestampCaptured`
  - `complianceNotes` (what permissions exist for storage/usage)

- **CompileArtifact**
  - `buildId`, `timestamp`
  - `pdfPath` (or buffer)
  - `logText`, `errors[]` (parsed)
  - `synctexPath` (for forward/inverse jumps)

- **AIEditProposal**
  - `proposalId`
  - `targetFile` (`main.tex`)
  - `diff` (unified diff or structured patch)
  - `rationale` (human‑readable)
  - `riskFlags` (possible fabrication, missing metric evidence, tense mismatch)
  - `requiresUserConfirmation` (almost always true)

This model enables a clean “plugin boundary” for future job sources while keeping the core feature (tailor resume to a job) independent from scraping specific sites.

## LaTeX editing, compilation, preview, and error‑fixing pipeline

### Editor, linting, and language intelligence

A strong match for your “Prism‑like” IDE feel is:
- **Monaco Editor** as the core editor; it’s the VS Code editor component, widely used and MIT licensed. citeturn11search0turn11search4  
- **TexLab** as the LaTeX Language Server Protocol implementation to power completions, symbols, and package indexing. citeturn11search2turn11search6turn11search31  
- **ChkTeX** as a linter for stylistic and semantic checks; it is widely integrated into LaTeX editor toolchains. citeturn4search19turn4search7  

### Compilation orchestration

For compilation, the standard automation tool is **latexmk**, designed to manage multi‑pass LaTeX compilation and auxiliary tools automatically. citeturn4search21turn4search9turn4search17 Overleaf’s documentation confirms latexmk is the compile driver in that ecosystem and that `latexmkrc` can customize compile behavior. citeturn11search28turn4search29

**Security requirement:** LaTeX compilation can execute external commands when shell escape is enabled (via `\write18` / `--shell-escape`), which is a well‑documented security risk. citeturn4search34turn4search10turn4search22 Even if your product is “single user,” templates imported from the internet or AI‑generated LaTeX can accidentally (or maliciously) introduce risky constructs, so you should:
- default to **no shell‑escape**,
- sandbox compilation in an isolated environment (container, unprivileged user, restricted filesystem).

Overleaf’s on‑prem documentation describes “sandboxed compiles” that run each project in its own secured Docker environment to achieve isolation between projects, which is a good reference pattern even for a desktop build (you can apply the same isolation concepts locally). citeturn11search7turn11search11

### PDF preview

For an embedded preview panel, **PDF.js** is the standard web‑tech PDF renderer, described as a general‑purpose, web‑standards platform for parsing/rendering PDFs. citeturn11search1turn11search5 This lets you replicate the “preview with PDF toolbar” experience inside the Electron renderer without relying on external viewers.

### Forward/inverse navigation (source ↔ PDF)

To match the IDE feel (especially for error fixing), implement SyncTeX support:

- SyncTeX is explicitly designed to synchronize between TeX source and typeset output (“navigate from the source document to the typeset material and vice versa”). citeturn13search1turn13search5  
- Editor ecosystems (e.g., AUCTeX) document forward and inverse search as core productivity features, with SyncTeX as a recommended correlation method. citeturn13search9  

Practical implication for your app:
- Ensure the TeX engine is invoked with SyncTeX enabled (usually already default in modern distributions, but design for explicit enablement).
- Persist the `.synctex.gz` artifact per compile.
- Provide “jump to PDF” on editor cursor and “jump to source” on PDF click (within the constraints of PDF.js event mapping).

## AI system design using entity["company","Mistral AI","llm startup france"] models and Nemotron coding support

### Model integration options

Mistral provides an API with chat completions and an official specification; this is the most straightforward way to integrate AI edits into a TypeScript app. citeturn10search0turn10search6turn10search3  
Mistral also releases open‑weight models under permissive licensing (e.g., Mistral 7B and Mixtral under Apache 2.0), which supports an alternative design: local or self‑hosted inference for privacy‑sensitive users. citeturn10search4turn10search1turn10search21

If you intend to feed this spec into a Nemotron coding model, note that entity["company","NVIDIA","gpu maker us"] provides a “Nemotron Open Model License” describing commercial usability and derivative works, and clarifying that NVIDIA does not claim ownership of outputs generated by the model. citeturn10search2turn10search5

### What the AI should (and should not) do

To build user trust and reduce harm, your AI assistant should be constrained to **transformations of user‑provided facts**, not generation of new facts. A robust design is:

- **Extract**: parse job description → structured requirements/keywords.
- **Map**: match requirements to existing resume evidence (projects, roles, skills) the user already has in the project.
- **Propose**: produce minimal diffs to adjust wording, emphasize relevant skills, reorder bullets, improve clarity, and fix LaTeX formatting.
- **Verify**: flag any proposed addition that lacks evidence in the user’s data (e.g., “+30% performance improvement”) as “needs proof” and require a user‑entered metric.

This aligns with mainstream guidance that AI can support drafting but the user must ensure accuracy and integrity. citeturn9search2

### AI edit representation: patch‑first, not text‑blob

To integrate cleanly with LaTeX and the Prism‑like workflow, represent AI output as:
- a unified diff (or structured patch) against `main.tex`,
- a rationale panel,
- and “apply / reject / edit” controls.

This reduces the “AI overwrote my resume” failure mode and makes undo/version tracking straightforward.

### ATS‑aware tailoring, without claiming “guaranteed pass”

Your system can legitimately support ATS‑aware editing by surfacing:
- keyword gaps compared to the job posting,
- section placement suggestions,
- and formatting linting (avoid complex constructs that break parsers).

However, avoid absolute claims like “will pass ATS.” Public guidance emphasizes **using job listing keywords** and keeping content readable, but ATS behavior varies. citeturn9search30turn14search3

## Security, privacy, and compliance requirements for an India‑first product

Because resumes contain sensitive personal data (identity, contact info, employment history), your tool must be designed as a privacy‑first system.

### India: DPDP Act and DPDP Rules 2025

India’s Digital Personal Data Protection Act, 2023 is explicitly intended to regulate processing of digital personal data while recognizing individuals’ right to protect personal data. citeturn8search0turn8search6  
The Government notified the Digital Personal Data Protection Rules, 2025 (per the PIB press release), describing them as giving full effect to the DPDP Act and establishing a practical system around consent, protection, and responsible use. citeturn8search3turn8search10

**Product implications (practical controls):**
- Explicit consent and clear notice for any cloud processing of resume data (especially if AI calls are remote).
- Data minimization: store only what is needed for the project; avoid storing job‑board credentials or session cookies.
- User controls for deletion/export.
- Breach readiness: logging, key management, incident response.

### Desktop app security posture (Electron hardening)

Electron security guidance highlights:
- the importance of `contextIsolation`,
- that enabling Node integration in a renderer can disable sandboxing,
- and that sandboxing can be enforced and is default behavior in newer Electron versions. citeturn4search0turn4search4turn4search8turn4search20  

Given you will render PDFs and potentially untrusted HTML (job descriptions), the baseline should be:
- no remote content in privileged windows,
- strict Content Security Policy,
- PDF rendering isolated from the main UI context if possible,
- minimal IPC surface.

### Risk register for your original “job harvesting” vision

The build risks are not just technical; they are existential product risks:

- **Platform enforcement risk**: LinkedIn explicitly prohibits crawlers/bots/extensions that scrape or automate activity, with enforcement including bans. citeturn5view2  
- **Partner access risk**: LinkedIn’s job posting integration is restricted and (as of Feb 2026) not accepting new partnerships for the Job Posting API, meaning official access is not an available baseline assumption. citeturn5view3  
- **Terms conflict risk**: Internshala explicitly prohibits scraping/crawling/data mining, including for AI/LLM development without written consent. citeturn6view0  
- **Legal/contract risk**: scraping disputes illustrate that even if certain anti‑hacking claims fail, ToS breach claims can still prevail and result in injunctions. citeturn7search25turn7search28turn7search32  
- **Privacy regulator risk**: scraping/collecting contact details from LinkedIn has been sanctioned by regulators (CNIL action against KASPR). citeturn7search2turn7search6

**Therefore:** treat “aggregate all jobs from LinkedIn/Internshala/Naukri” as an enterprise partnership track, not an MVP feature.

### MVP scope that is feasible and still compelling

A compliance‑first MVP can still deliver most user value:

1) **Job Import**: paste job description / import from a user‑provided URL; optionally support RSS feeds where explicitly provided. citeturn12search5  
2) **Resume Project Templates**: LaTeX templates with ATS‑safe structure.  
3) **IDE Workflow**: Monaco + PDF.js + latexmk; compile and preview loop. citeturn11search0turn11search1turn4search17turn4search21  
4) **Diagnostics**: ChkTeX + log parser + clickable errors. citeturn4search19turn4search7  
5) **AI Tailoring**: patch‑based edits using Mistral models (API or local), with strong anti‑fabrication constraints. citeturn10search0turn10search4  
6) **Navigation polish**: SyncTeX forward/inverse search to match the “real IDE” feel. citeturn13search1turn13search9

This preserves your “exact Prism UI + LaTeX + AI edits” vision while removing the single highest‑risk dependency: non‑authorized job board harvesting.
---

## Implementation Status

### ✅ Completed

1. **Modern UI Pages Created (Flutter):**
   - `modern_login_page.dart` - OAuth login/signup with animations
   - `modern_dashboard.dart` - Collapsible sidebar navigation
   - `modern_resumes_page.dart` - Grid/list view resume management
   - `modern_job_search.dart` - Job search with filters
   - `modern_settings_page.dart` - API keys and preferences

2. **Providers:**
   - `auth_provider.dart` - Auth state management
   - Integrated into `main.dart` with MultiProvider

3. **Services:**
   - Enhanced `job_aggregation_service.dart` - Improved RemoteOkConnector
   - `auth_service.dart` - OAuth flows
   - `mistral_ai_service.dart` - AI tailoring
   - `latex_compiler_service.dart` - Compilation

4. **Main App Integration:**
   - `main.dart` - Complete app shell with all modern pages
   - AppShell with login flow and dashboard navigation
   - Responsive design with dark theme

5. **Configuration:**
   - `pubspec.yaml` - Added `flutter_animate: ^4.5.0`

### 📋 Pending

- [ ] Complete OAuth flow - Implement actual Google/GitHub/LinkedIn OAuth redirects
- [ ] Integrate services - Connect Mistral AI, job search APIs
- [ ] Add ChkTeX linting - LaTeX error checking
- [ ] Implement template system - Resume templates
- [ ] Test the application - Run `flutter run` to verify modern UI

### 📁 Relevant Files

**New Modern UI Files:**
- `cv_flutter/lib/pages/modern_login_page.dart`
- `cv_flutter/lib/pages/modern_resumes_page.dart`
- `cv_flutter/lib/pages/modern_job_search.dart`
- `cv_flutter/lib/pages/modern_settings_page.dart`
- `cv_flutter/lib/widgets/modern_dashboard.dart`

**Modified Files:**
- `cv_flutter/lib/main.dart` - Complete rewrite with modern UI
- `cv_flutter/lib/providers/auth_provider.dart` - Created
- `cv_flutter/lib/services/job_aggregation_service.dart` - Enhanced
- `cv_flutter/pubspec.yaml` - Added flutter_animate

---

## Implementation Status (Updated)

### ✅ Completed

1. **Modern UI Pages Created (Flutter):**
   - `modern_login_page.dart` - OAuth login/signup with animations
   - `modern_dashboard.dart` - Collapsible sidebar navigation
   - `modern_resumes_page.dart` - Grid/list view resume management
   - `modern_job_search.dart` - Job search with filters
   - `modern_settings_page.dart` - API keys and preferences

2. **Providers:**
   - `auth_provider.dart` - Auth state management
   - `ai_provider.dart` - AI service integration with Mistral AI
   - Integrated into `main.dart` with MultiProvider

3. **Services:**
   - Enhanced `job_aggregation_service.dart` - Improved RemoteOkConnector
   - `auth_service.dart` - OAuth flows (Google, GitHub, LinkedIn)
   - `mistral_ai_service.dart` - AI tailoring with keyword analysis
   - `template_service.dart` - Resume template management
   - `latex_compiler_service.dart` - Compilation

4. **Main App Integration:**
   - `main.dart` - Complete app shell with all modern pages
   - AppShell with login flow and dashboard navigation
   - Responsive design with dark theme
   - Environment variable configuration for API keys

5. **Configuration:**
   - `pubspec.yaml` - Added `flutter_animate: ^4.5.0`, `url_launcher: ^6.3.2`, `app_links: ^6.4.1`

### 📋 Pending

- [ ] Complete OAuth flow - Implement actual Google/GitHub/LinkedIn OAuth redirects
- [ ] Integrate services - Connect Mistral AI, job search APIs  
- [ ] Add ChkTeX linting - LaTeX error checking
- [ ] Implement template system - Resume templates
- [ ] Test the application - Run `flutter run` to verify modern UI

### 📁 Relevant Files

**New Modern UI Files:**
- `cv_flutter/lib/pages/modern_login_page.dart`
- `cv_flutter/lib/pages/modern_resumes_page.dart`
- `cv_flutter/lib/pages/modern_job_search.dart`
- `cv_flutter/lib/pages/modern_settings_page.dart`
- `cv_flutter/lib/widgets/modern_dashboard.dart`

**New Service Files:**
- `cv_flutter/lib/services/template_service.dart` - Template management
- `cv_flutter/lib/providers/ai_provider.dart` - AI service provider

**Modified Files:**
- `cv_flutter/lib/main.dart` - Complete rewrite with modern UI and AI integration
- `cv_flutter/lib/providers/auth_provider.dart` - Enhanced with OAuth flows
- `cv_flutter/lib/services/auth_service.dart` - Added GitHub OAuth, URL launching
- `cv_flutter/lib/services/job_aggregation_service.dart` - Enhanced RemoteOkConnector
- `cv_flutter/pubspec.yaml` - Added flutter_animate, url_launcher, app_links
- `cv_flutter/lib/widgets/template_selection_dialog.dart` - Template picker UI

### 🔧 Environment Configuration

To enable full functionality, set these environment variables:

```bash
# OAuth Configuration (obtain from respective developer consoles)
export GOOGLE_CLIENT_ID="your-google-client-id"
export LINKEDIN_CLIENT_ID="your-linkedin-client-id" 
export LINKEDIN_CLIENT_SECRET="your-linkedin-client-secret"
export GITHUB_CLIENT_ID="your-github-client-id"

# AI Configuration  
export MISTRAL_API_KEY="your-mistral-api-key"

# Then run:
flutter run -d macos --dart-define=GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID \
  --dart-define=LINKEDIN_CLIENT_ID=$LINKEDIN_CLIENT_ID \
  --dart-define=LINKEDIN_CLIENT_SECRET=$LINKEDIN_CLIENT_SECRET \
  --dart-define=GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID \
  --dart-define=MISTRAL_API_KEY=$MISTRAL_API_KEY
```

## OAuth Compliance Fix

- [x] Fixed Google OAuth 2.0 policy compliance issue by switching to  package
- [x] Uses system browser flow instead of embedded webview
- [x] Proper OAuth client configuration for desktop apps
- [x] Maintains same API surface in AuthProvider


## OAuth Compliance Fix

- [x] Fixed Google OAuth 2.0 policy compliance issue by switching to  package
- [x] Uses system browser flow instead of embedded webview
- [x] Proper OAuth client configuration for desktop apps
- [x] Maintains same API surface in AuthProvider

