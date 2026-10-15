# CVStar — Job-Aware LaTeX Resume Workspace

[![Live Demo](https://img.shields.io/badge/Live%20Demo-cvstar--workspace.vercel.app-6366f1?style=for-the-badge&logo=vercel&logoColor=white)](https://cvstar-workspace.vercel.app)
[![ATS Engine](https://img.shields.io/badge/ATS%20Tailoring-Mistral%20%2F%20Taxonomy%20Engine-ec4899?style=for-the-badge&logo=openai&logoColor=white)](https://cvstar-workspace.vercel.app)
[![Tests](https://img.shields.io/badge/Test%20Suite-6%2F6%20Passing-10b981?style=for-the-badge&logo=vitest&logoColor=white)](https://cvstar-workspace.vercel.app)

> **Live Interactive Workspace**: **[https://cvstar-workspace.vercel.app](https://cvstar-workspace.vercel.app)**
> 
> A modern, Linear/Kestra-tier LaTeX resume IDE running directly in the browser. Features split-screen live LaTeX preview, real-time ChkTeX syntax diagnostics, automated ATS match scoring against real job descriptions, keyword gap analysis, Google XYZ bullet optimization, and surgical diff patching.

---

## Workspace Architecture

```
                  +-------------------------------------------------+
                  |          CVStar Modern React 18 Workspace       |
                  +------------------------+------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
     +------------------------------+             +-------------------------------+
     |      LaTeX Source Editor     |             |       Live Resume Canvas      |
     | - Real-time syntax highlight |             | - High-res A4 document engine |
     | - AST line & bullet tracking |             | - Real-time typography sync   |
     | - Surgical patch applicator  |             | - Dynamic zoom (70% - 140%)   |
     +--------------+---------------+             +---------------+---------------+
                    |                                             ^
                    |                                             |
                    +----------------------+----------------------+
                                           |
                                           v
                  +-------------------------------------------------+
                  |            AI Job Tailoring Engine              |
                  | - Multi-source Job Intake (Rakuten, Stripe, etc)|
                  | - ATS Match Index (0 - 100%)                    |
                  | - Missing vs. Underused Keyword Matrix          |
                  | - Google XYZ Bullet Rewriter (Quantified Impact)|
                  | - ChkTeX & Font Ligature Compliance Linter      |
                  +-------------------------------------------------+
```

---

## Core Capabilities

### 1. Split-View LaTeX IDE & Instant Preview
- Full LaTeX code editing with line numbers, code folding, and template selection (Jake's Resume, Modern High-Density SWE, and Academic Research).
- Real-time client-side document canvas that renders publication-grade typography, small-caps section headers, bullet lists, dates, and locations without server round-trips.

### 2. AI Job-Aware Tailoring Engine
- **Target Job Profiles**: Pre-loaded with realistic tech targets (*Rakuten Kobo SDE Intern*, *Stripe Backend Systems Engineer*, *Google SRE*) or paste custom job descriptions.
- **ATS Match Score**: Computes alignment percentage based on required technical taxonomy versus candidate resume content.
- **Keyword Gap Matrix**: Categorizes keywords into **Matched** (emerald), **Missing** (rose), and **Underused** (amber).
- **Google XYZ Bullet Optimization**: Analyzes resume bullet points and provides before/after rewrites ("Accomplished [X] measured by [Y] by doing [Z]") with impact gain metrics.
- **Surgical Patch Insertion**: One-click "Apply Patch to Resume" button modifies the LaTeX source in place while preserving curly braces, macros, and formatting structure.

### 3. ChkTeX & ATS Compliance Diagnostics
- Inspects code for common ATS hazards:
  - Font ligature parsing anomalies (`pdfgentounicode=1` checks).
  - Machine-readable column flow (validates `tabularx` over standard `tabular`).
  - Unescaped `%` characters and unbalanced brace syntax.

### 4. Enterprise Desktop Deployment (Electron)
- In addition to the web workspace, CVStar includes an audited Electron desktop container (`src/main/index.ts`):
  - Strictly enforces `contextIsolation: true` and `nodeIntegration: false`.
  - Bridges local `latexmk` subprocess compilation disabling unsafe shell escape.
  - Native file dialogs for opening and saving `.tex` files.

---

## Automated Verification Suite

CVStar includes a 6-part test suite verifying core AST, NLP, and regex algorithms:

| Test Name | Pipeline Component | Assertion Verified |
| :--- | :--- | :--- |
| `testLatexAstBulletParser` | AST Parser | Extracts `\resumeItem{...}` and section headers without regex backtracking. |
| `testKeywordExtractionTaxonomy` | NLP Taxonomy | Identifies languages, databases, and frameworks accurately across input text. |
| `testAtsScoreFormulaBoundaries` | Score Engine | Asserts ATS score is mathematically bounded `[0, 100]` with proper weighting. |
| `testBulletRewriteXyzFormula` | Bullet Optimizer | Enforces active verbs, metric presence, and impact delta calculations. |
| `testSurgicalPatchDelimiterIntegrity` | Patch Engine | Verifies replacing bullet strings preserves surrounding curly braces and delimiters. |
| `testLinterCleanSyntax` | ChkTeX Linter | Validates clean standard templates trigger 0 syntax or brace mismatch errors. |

---

## Running Locally

```bash
# 1. Clone repository
git clone https://github.com/RedHolger/Manu-Vashisth-Personal.git
cd Manu-Vashisth-Personal/cvstar

# 2. Install dependencies
npm install --legacy-peer-deps

# 3. Run modern web workspace (Vite)
npm run dev
# Open http://localhost:5176

# 4. Run automated test suite
node --experimental-strip-types --test "tests/*.test.ts"

# 5. Build production bundle
npm run build
```