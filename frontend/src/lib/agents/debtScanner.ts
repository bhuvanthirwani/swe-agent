// ============================================================
// Technical Debt Scanner — Types and stub report generator
// ============================================================

export interface DebtHotspot {
  type: 'architectural' | 'testing' | 'documentation' | 'security' | 'dependency' | 'performance';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  description: string;
  recommendation: string;
  file?: string;
}

export interface TechnicalDebtReport {
  /** Overall debt grade: A–F */
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  /** Debt score on a 0–10 scale (10 = highest debt) */
  debtScore: number;
  /** Human-readable summary */
  summary: string;
  /** Per-category scores (0–10, lower is better) */
  categories: {
    architectural: number;
    testing: number;
    documentation: number;
    security: number;
    dependency: number;
    performance: number;
  };
  /** Top debt hotspots sorted by severity */
  hotspots: DebtHotspot[];
  /** Estimated developer hours needed to fix the debt */
  estimatedHoursToRemediate: number;
}
