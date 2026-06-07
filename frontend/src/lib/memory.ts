// ============================================================
// Memory — Cross-session preference & context persistence
// Stores user preferences extracted from analyst outputs so
// the pipeline can personalise future runs automatically.
// Gap #8: Session Memory
// ============================================================

const MEMORY_KEY = 'mao_session_memory';

export interface MemoryState {
  /** Number of pipeline runs completed in this browser profile */
  runCount: number;
  /** Tech stack preferences extracted from past runs */
  preferredTechStack: string[];
  /** Preferred coding style notes */
  codingPreferences: string[];
  /** Recent project domains/topics */
  recentTopics: string[];
  /** Timestamp of last update */
  lastUpdatedAt: number;
}

const DEFAULT_MEMORY: MemoryState = {
  runCount: 0,
  preferredTechStack: [],
  codingPreferences: [],
  recentTopics: [],
  lastUpdatedAt: 0,
};

/**
 * Load persisted memory from localStorage.
 * Safe to call on server (returns defaults).
 */
export function loadMemory(): MemoryState {
  if (typeof window === 'undefined') return { ...DEFAULT_MEMORY };
  try {
    const raw = localStorage.getItem(MEMORY_KEY);
    if (!raw) return { ...DEFAULT_MEMORY };
    return { ...DEFAULT_MEMORY, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_MEMORY };
  }
}

/**
 * Merge partial updates into stored memory and persist.
 */
export function updateMemory(updates: Partial<MemoryState>): void {
  if (typeof window === 'undefined') return;
  try {
    const current = loadMemory();
    const next: MemoryState = {
      ...current,
      ...updates,
      runCount: updates.runCount ?? current.runCount,
      preferredTechStack: dedupe([
        ...current.preferredTechStack,
        ...(updates.preferredTechStack ?? []),
      ]).slice(0, 20),
      codingPreferences: dedupe([
        ...current.codingPreferences,
        ...(updates.codingPreferences ?? []),
      ]).slice(0, 20),
      recentTopics: dedupe([
        ...(updates.recentTopics ?? []),
        ...current.recentTopics,
      ]).slice(0, 10),
      lastUpdatedAt: Date.now(),
    };
    localStorage.setItem(MEMORY_KEY, JSON.stringify(next));
  } catch { /* ignore */ }
}

/**
 * Clear all stored memory (useful for tests / settings reset).
 */
export function clearMemory(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(MEMORY_KEY);
}

/**
 * Extract user preferences from the requirements-analyst output text.
 * Returns a partial MemoryState ready to be merged with updateMemory().
 */
export function extractPreferencesFromAnalystOutput(
  analystOutput: string,
  requirement: string
): Partial<MemoryState> {
  const techStack: string[] = [];
  const codingPrefs: string[] = [];

  // Common tech stack keywords to watch for
  const TECH_KEYWORDS = [
    'React', 'Next.js', 'Vue', 'Angular', 'Svelte',
    'TypeScript', 'JavaScript', 'Python', 'Go', 'Rust', 'Java',
    'Node.js', 'FastAPI', 'Django', 'Flask', 'Express',
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite',
    'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
    'GraphQL', 'REST', 'tRPC', 'Prisma', 'Drizzle',
    'Tailwind', 'shadcn', 'Material UI', 'Radix',
  ];

  const lower = analystOutput.toLowerCase();
  for (const tech of TECH_KEYWORDS) {
    if (lower.includes(tech.toLowerCase())) {
      techStack.push(tech);
    }
  }

  // Extract coding preference hints
  if (lower.includes('typescript') || lower.includes('strict')) {
    codingPrefs.push('strict TypeScript');
  }
  if (lower.includes('test') || lower.includes('tdd')) {
    codingPrefs.push('test-driven');
  }
  if (lower.includes('clean') || lower.includes('solid')) {
    codingPrefs.push('clean architecture');
  }
  if (lower.includes('microservice') || lower.includes('micro-service')) {
    codingPrefs.push('microservices');
  }
  if (lower.includes('monolith')) {
    codingPrefs.push('monolith');
  }

  // Derive topic from the requirement (first 60 chars)
  const topic = requirement.trim().split(/\s+/).slice(0, 6).join(' ');

  return {
    preferredTechStack: techStack,
    codingPreferences: codingPrefs,
    recentTopics: topic ? [topic] : [],
  };
}

// ─── Helpers ─────────────────────────────────────────────────

function dedupe<T>(arr: T[]): T[] {
  return [...new Set(arr)];
}
