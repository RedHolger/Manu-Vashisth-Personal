export interface ResumeProject {
  id: string;
  name: string;
  targetRole: string;
  templateId: 'jake' | 'modern' | 'research';
  latex: string;
  lastCompiled: string;
  matchScore: number;
}

export interface JobTarget {
  id: string;
  company: string;
  role: string;
  description: string;
  keywords: string[];
}

export interface BulletRewrite {
  id: string;
  section: string;
  original: string;
  rewritten: string;
  rationale: string;
  metricGain: string;
  applied: boolean;
}

export interface AtsAnalysisResult {
  matchScore: number;
  matchedKeywords: string[];
  missingKeywords: string[];
  underusedKeywords: string[];
  bulletRewrites: BulletRewrite[];
  complianceCheck: {
    passed: boolean;
    issues: string[];
    score: number;
  };
}

export interface LinterDiagnostic {
  line: number;
  severity: 'error' | 'warning' | 'info';
  code: string;
  message: string;
}
