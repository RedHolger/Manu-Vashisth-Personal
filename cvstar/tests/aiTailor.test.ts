import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { extractKeywords, analyzeResume, applyBulletPatch, lintLatex } from '../src/services/aiTailoringEngine.ts';
import { JAKE_TEMPLATE } from '../src/templates/sampleResumes.ts';

describe('CVStar AI Tailoring & LaTeX Analysis Pipeline', () => {
  it('extracts technical skills taxonomy from raw text', () => {
    const text = 'Required skills: Java 17, Spring Boot, PostgreSQL 16, T-SQL, Docker, React, and Git.';
    const keywords = extractKeywords(text);

    assert.ok(keywords.includes('java'));
    assert.ok(keywords.includes('postgresql'));
    assert.ok(keywords.includes('t-sql'));
    assert.ok(keywords.includes('docker'));
    assert.ok(keywords.includes('react'));
  });

  it('computes ATS match score within [0, 100] bounds', () => {
    const jobDesc = 'Seeking an engineer with Java, React, SQL Server, and Docker experience.';
    const analysis = analyzeResume(JAKE_TEMPLATE, jobDesc);

    assert.ok(analysis.matchScore >= 40 && analysis.matchScore <= 100);
    assert.ok(analysis.matchedKeywords.length > 0);
  });

  it('identifies missing target keywords from job description', () => {
    const jobDesc = 'Must have extensive Kubernetes and Kafka production experience.';
    const analysis = analyzeResume(JAKE_TEMPLATE, jobDesc);

    assert.ok(analysis.missingKeywords.includes('KAFKA'));
    assert.ok(analysis.missingKeywords.includes('KUBERNETES'));
  });

  it('rewrites weak bullets into quantified impact statements', () => {
    const jobDesc = 'Looking for high-impact backend performance tuning.';
    const analysis = analyzeResume(JAKE_TEMPLATE, jobDesc);

    assert.ok(analysis.bulletRewrites.length > 0);
    const rewrite = analysis.bulletRewrites[0];
    assert.notEqual(rewrite.original, rewrite.rewritten);
    assert.ok(rewrite.metricGain.includes('%'));
  });

  it('surgically applies patches to LaTeX source without breaking delimiter syntax', () => {
    const jobDesc = 'Seeking Java and React engineer.';
    const analysis = analyzeResume(JAKE_TEMPLATE, jobDesc);
    const rewrite = analysis.bulletRewrites[0];

    const patched = applyBulletPatch(JAKE_TEMPLATE, rewrite);
    assert.ok(patched.includes(rewrite.rewritten));
    assert.ok(!patched.includes(rewrite.original));
  });

  it('linter validates clean LaTeX without unmatched braces', () => {
    const diagnostics = lintLatex(JAKE_TEMPLATE);
    const errors = diagnostics.filter((d) => d.severity === 'error');
    assert.equal(errors.length, 0);
  });
});
