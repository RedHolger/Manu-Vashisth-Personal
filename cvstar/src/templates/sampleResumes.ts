export const JAKE_TEMPLATE = `%-------------------------
% Resume in LaTeX - Jake's Template (ATS-Optimized)
% Target: Rakuten Kobo / Tier-1 Software Engineering
%-------------------------

\\documentclass[letterpaper,11pt]{article}

\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage[english]{babel}
\\usepackage{tabularx}

\\pagestyle{fancy}
\\fancyhf{}
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

% Adjust margins
\\addtolength{\\oddsidemargin}{-0.5in}
\\addtolength{\\evensidemargin}{-0.5in}
\\addtolength{\\textwidth}{1in}
\\addtolength{\\topmargin}{-.5in}
\\addtolength{\\textheight}{1.0in}

\\urlstyle{same}

\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}

% Sections formatting
\\titleformat{\\section}{
  \\vspace{-4pt}\\scshape\\raggedright\\large
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]

\\begin{document}

%----------HEADING----------
\\begin{center}
    \\textbf{\\Huge \\scshape Manu Vashisth} \\\\ \\vspace{1pt}
    \\small Limerick, Ireland $|$ +353 89 439 7650 $|$ \\href{mailto:manuvashisth963@gmail.com}{\\underline{manuvashisth963@gmail.com}} $|$ 
    \\href{https://linkedin.com/in/manu-vashisth-9366b2219/}{\\underline{linkedin.com/in/manu-vashisth}} $|$
    \\href{https://github.com/RedHolger}{\\underline{github.com/RedHolger}}
\\end{center}

%-----------EDUCATION-----------
\\section{Education}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {University of Limerick}{Limerick, Ireland}
      {Master of Science in Artificial Intelligence and Machine Learning}{2026 -- 2027}
    \\resumeSubheading
      {Guru Gobind Singh Indraprastha University}{Delhi, India}
      {Bachelor of Technology in Computer Science; Grade: 83.1\\%}{2021 -- 2025}
  \\resumeSubHeadingListEnd

%-----------TECHNICAL SKILLS-----------
\\section{Technical Skills}
 \\begin{itemize}[leftmargin=0.15in, label={}]
    \\small{\\item{
     \\textbf{Languages}{: Java 17+, Python, TypeScript, JavaScript, SQL, T-SQL, C++} \\\\
     \\textbf{Frameworks & Tools}{: Spring Boot, React, Vite, Node.js, Docker, Git, Electron, REST APIs} \\\\
     \\textbf{Database Systems}{: PostgreSQL 16, Microsoft SQL Server 2022, SQLite, Redis}
    }}
 \\end{itemize}

%-----------EXPERIENCE-----------
\\section{Experience}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {WorldRef}{Aug. 2025 -- Apr. 2026}
      {Software Engineer (Applied AI and Systems)}{Delhi, India}
      \\resumeItemListStart
        \\resumeItem{Architected Spring backend and React frontend workflows for an industrial B2B marketplace handling transactions across deals, RFQs, quotations, and product catalogues.}
        \\resumeItem{Refactored quotation reconciliation to process line items in-memory, reducing quote response latency by 20\\% and slashing database round-trips by 4--30 times.}
        \\resumeItem{Migrated critical document uploads to Amazon S3 presigned URLs, reducing file upload latencies by 3x.}
      \\resumeItemListEnd
  \\resumeSubHeadingListEnd

%-----------PROJECTS-----------
\\section{Key Engineering Projects}
    \\resumeSubHeadingListStart
      \\resumeProjectHeading
          {\\textbf{ReadingQueue} $|$ \\emph{Java 17, PostgreSQL 16, SQL Server 2022, React, T-SQL}}{}
          \\resumeItemListStart
            \\resumeItem{Engineered a zero-dependency Java 17 REST service implementing dual-dialect migrations across PostgreSQL 16 and Microsoft SQL Server 2022 (T-SQL).}
            \\resumeItem{Implemented ACID ownership transfer with forced mid-transaction failure injection, verifying atomic rollback across 9/9 green JUnit test contracts.}
          \\resumeItemListEnd
      \\resumeProjectHeading
          {\\textbf{CVStar} $|$ \\emph{Electron, React, TypeScript, Monaco Editor, PDF.js, latexmk}}{}
          \\resumeItemListStart
            \\resumeItem{Built a desktop LaTeX resume workspace integrating real-time compilation, SyncTeX bidirectional navigation, and job-description ATS tailoring.}
            \\resumeItem{Enforced strong security isolation in Electron (contextIsolation, no-shell-escape) and structured job data ingestion compliant with GDPR and DPDP 2023.}
          \\resumeItemListEnd
    \\resumeSubHeadingListEnd

\\end{document}
`;

export const JOB_TARGET_PRESETS = [
  {
    id: 'rakuten-kobo',
    company: 'Rakuten Kobo',
    role: 'Software Developer Intern (Dublin)',
    keywords: ['Java', 'React', 'T-SQL', 'SQL Server', 'REST APIs', 'Git', 'Relational Databases', 'Transactions'],
    description: `Rakuten Kobo is seeking a Software Developer Intern in Dublin.
Key requirements:
- Strong programming experience in Java or C#
- Practical familiarity with modern frontend web technologies (React, TypeScript)
- Solid database querying skills using T-SQL / SQL Server or PostgreSQL
- Understanding of RESTful API design, version control with Git, and transactional integrity
- Proactive debugging, test-driven mindset, and clear code documentation.`,
  },
  {
    id: 'stripe-backend',
    company: 'Stripe',
    role: 'Backend Systems Engineer',
    keywords: ['Java', 'Distributed Systems', 'PostgreSQL', 'Transactions', 'ACID', 'Idempotency', 'API Design'],
    description: `Stripe builds economic infrastructure for the internet.
Requirements:
- Robust backend development experience in Java or Go
- Deep knowledge of relational database internals, write-ahead logging, and ACID isolation levels
- Experience building idempotent payment workflows and resilient distributed systems
- Dedication to rigorous testing and automated failure recovery.`,
  },
  {
    id: 'google-sre',
    company: 'Google',
    role: 'Site Reliability Engineering (SRE) Intern',
    keywords: ['Python', 'Linux', 'Distributed Systems', 'SLO', 'Debugging', 'Docker', 'Automation'],
    description: `Google SRE balances software engineering and systems reliability.
Requirements:
- Experience writing software in Python, Go, C++, or Java
- Systems debugging skills in Linux environments (networking, file systems, IPC)
- Understanding of Service Level Objectives (SLOs), canary deployments, and error budgets
- Strong problem solving and post-mortem analysis capability.`,
  },
];
