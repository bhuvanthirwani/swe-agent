// ============================================================
// Compliance Agent — Types and stub report structure
// ============================================================

export interface ComplianceViolation {
  rule: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  remediation: string;
  framework?: string;
}

export interface FrameworkScore {
  framework: string;
  score: number;   // 0–100
  passed: boolean;
  violations: number;
}

export interface ComplianceReport {
  /** Overall pass/fail/warning status */
  overallStatus: 'PASS' | 'FAIL' | 'WARNING';
  /** Composite score 0–100 */
  overallScore: number;
  /** Human-readable summary */
  summary: string;
  /** Per-framework breakdown */
  frameworks: FrameworkScore[];
  /** Violations at critical severity */
  criticalViolations: ComplianceViolation[];
  /** All violations */
  violations: ComplianceViolation[];
  /** Estimated hours to reach full compliance */
  estimatedComplianceHours: number;
}
