# Design: Mock Mode Implementation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  NEXT_PUBLIC_DATA_SOURCE=mock (environment variable)   │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴──────────────────┐
         │  Intercept at Data Layer     │
         └───────────┬──────────────────┘
                     │
      ┌──────────────┼──────────────────────┐
      │              │                      │
   ┌──▼──┐      ┌────▼────┐         ┌──────▼──────┐
   │ Hook│      │ Actions │         │  Firebase   │
   │Layer│      │  Layer  │         │    Layer    │
   └──┬──┘      └────┬────┘         └──────┬──────┘
      │              │                      │
┌─────▼──────┐  ┌────▼────┐         ┌──────▼──────┐
│useLiveJobs │  │analyze  │         │ isMockMode  │
│   .ts      │  │  .ts    │         │  flag       │
└─────┬──────┘  └────┬────┘         └──────┬──────┘
      │              │                      │
  ┌───▼───┐      ┌───▼───┐             ┌───▼───┐
  │ MOCK  │      │ MOCK  │             │ MOCK  │
  │ Hook  │      │  API  │             │  N/A  │
  └───────┘      └───────┘             └───────┘
      │              │                      │
      └──────────────┴──────────────────────┘
                     │
              ┌──────▼───────┐
              │ UI Components│
              │ (unchanged)  │
              └──────────────┘
```

## File Structure

```
frontend/
├── lib/
│   ├── mock/
│   │   ├── mockData.ts           # 20+ pre-defined jobs
│   │   ├── useMockLiveJobs.ts    # Mock Firestore hook
│   │   └── mockApiHandlers.ts    # Mock backend API functions
│   ├── hooks/
│   │   └── useLiveJobs.ts        # MODIFIED: 3 lines added
│   └── firebase.ts               # MODIFIED: 1 export added
├── app/
│   ├── actions/
│   │   └── analyze.ts            # MODIFIED: 3 lines added
│   └── hitl/
│       └── page.tsx              # MODIFIED: ~15 lines (fetch wrappers)
├── .env.mock                     # NEW: Environment config for mock mode
└── package.json                  # MODIFIED: Add dev:mock script
```

## Component Design

### 1. mockData.ts

**Purpose**: Centralized storage of all mock job data.

**Exports**:
```typescript
export interface MockJob {
  id: string;
  thread_id: string;
  status: string;
  final_action: "Approve" | "Block" | "Human Review";
  title: string;
  description: string;
  price: number;
  image_url: string;
  risk_score: number;
  uncertainty: number;
  reasoning: string;
  signals: { ... };
  policy_violations?: Array<{ ... }>;
  policy_citations?: Array<{ ... }>;
  risk_breakdown?: Array<{ ... }>;
  features: { ... };
  min_price?: number;
  max_price?: number;
  routing_reason?: string;
  created_at: string;
  last_update: string;
  trace: Array<{ ... }>;
}

export const MOCK_JOBS: MockJob[];
```

**Implementation Notes**:
- Use helper functions `hoursAgo(n)` and `minutesAgo(n)` for realistic timestamps
- Use `buildTrace(jobId, finalAction, riskScore)` to generate consistent trace structures
- Group jobs by decision type with clear comments
- Use public image URLs (Unsplash) for most products
- Ensure all prices are in ARS (Argentine Pesos) circa 2026 rates

**Data Distribution**:
- 8 APPROVE jobs: job-approve-001 through job-approve-008
- 7 BLOCK jobs: job-block-001 through job-block-007
- 5 HUMAN_REVIEW jobs: job-review-001 through job-review-005

---

### 2. useMockLiveJobs.ts

**Purpose**: Mock implementation of the Firestore subscription hook.

**Interface** (must match `useLiveJobs`):
```typescript
export function useMockLiveJobs(): {
  jobs: Job[];
  loading: boolean;
  error: Error | null;
}
```

**Implementation**:
```typescript
import { useState, useEffect } from 'react';
import { MOCK_JOBS } from './mockData';
import type { Job } from '../hooks/useLiveJobs';

export function useMockLiveJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Simulate initial loading delay
    const timer = setTimeout(() => {
      // Convert MockJob[] to Job[] (they should be compatible)
      setJobs(MOCK_JOBS as unknown as Job[]);
      setLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  return { jobs, loading, error };
}
```

**Optional Enhancement** (for more realistic demo):
- Simulate progressive job arrival every 10-15 seconds
- Use `setInterval` to add jobs to the list gradually

---

### 3. mockApiHandlers.ts

**Purpose**: Mock implementations of all backend API calls.

**Exports**:
```typescript
import { MOCK_JOBS } from './mockData';
import type { AnalysisResult, AnalyzeParams } from '@/app/actions/analyze';

/**
 * Mock upload - returns a fake job_id instantly
 */
export function mockUpload(params: any): Promise<{ job_id: string }> {
  return Promise.resolve({
    job_id: `mock-job-${Date.now()}`
  });
}

/**
 * Mock analyze - simulates agent processing delay, returns random job
 */
export async function mockAnalyze(
  params: AnalyzeParams
): Promise<{ result?: AnalysisResult; error?: string }> {
  // Simulate 3-4 second processing delay
  await new Promise(resolve => setTimeout(resolve, 3000 + Math.random() * 1000));

  // Return a random job from the HUMAN_REVIEW or BLOCK categories
  // (to make the demo interesting)
  const interestingJobs = MOCK_JOBS.filter(
    j => j.final_action === 'Human Review' || j.final_action === 'Block'
  );
  const randomJob = interestingJobs[Math.floor(Math.random() * interestingJobs.length)];

  return {
    result: randomJob as unknown as AnalysisResult
  };
}

/**
 * Mock get trace - returns the trace for a given job_id
 */
export async function mockGetTrace(jobId: string): Promise<any> {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 1500));

  const job = MOCK_JOBS.find(j => j.id === jobId || j.thread_id === jobId);
  if (!job) {
    throw new Error(`Job ${jobId} not found in mock data`);
  }

  return {
    trace: job.trace,
    job_id: jobId,
    status: 'completed'
  };
}

/**
 * Mock submit decision - logs and returns success
 */
export async function mockSubmitDecision(
  jobId: string,
  decision: 'Approve' | 'Block'
): Promise<{ ok: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  console.log(`[MOCK] Decision for ${jobId}: ${decision}`);
  return { ok: true };
}

/**
 * Mock get image URL - returns the image_url from the job
 */
export function mockGetImageUrl(jobId: string): string {
  const job = MOCK_JOBS.find(j => j.id === jobId || j.thread_id === jobId);
  return job?.image_url || '/placeholder.png';
}
```

**Implementation Notes**:
- All functions return Promises to maintain async interface compatibility
- Use realistic delays that match real API behavior
- `mockAnalyze` should favor returning interesting jobs (HUMAN_REVIEW or BLOCK) to make demos more engaging
- Log decisions to console for debugging

---

### 4. Modifications to Existing Files

#### lib/firebase.ts

**Change**: Add 1 export at the end:

```typescript
// Existing code...

export { app, db };

// NEW: Export mock mode flag
export const isMockMode = process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock';
```

**Rationale**: Centralize the mock mode check so other files can import it.

---

#### lib/hooks/useLiveJobs.ts

**Change**: Add 3 lines at the beginning of the hook:

```typescript
import { isMockMode } from '../firebase';
import { useMockLiveJobs } from '../mock/useMockLiveJobs';
// ...existing imports...

export function useLiveJobs() {
  // NEW: Redirect to mock in mock mode
  if (isMockMode) return useMockLiveJobs();

  // ...existing code unchanged...
}
```

**Rationale**: Single entry point for Firestore data, clean separation of mock and prod logic.

---

#### app/actions/analyze.ts

**Change**: Add branch at start of `analyzeProduct` function:

```typescript
import { mockAnalyze } from '@/lib/mock/mockApiHandlers';

export async function analyzeProduct(
  params: AnalyzeParams
): Promise<{ result?: AnalysisResult; error?: string }> {
  try {
    // NEW: Use mock handler in mock mode
    if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
      return mockAnalyze(params);
    }

    // ...existing code unchanged...
  } catch (err) {
    // ...existing error handling...
  }
}
```

**Rationale**: Intercept at the action layer before any backend calls are made.

---

#### app/hitl/page.tsx

**Change**: Wrap fetch calls with mock handlers (~15 lines total).

**Locations to modify**:
1. `handleSelectJob` - trace fetching
2. `handleDecision` - decision submission
3. `getImageUrl` (if exists) - image URL resolution

**Example**:
```typescript
import { mockGetTrace, mockSubmitDecision, mockGetImageUrl } from '@/lib/mock/mockApiHandlers';

// In handleSelectJob:
async function handleSelectJob(jobId: string) {
  setLoadingTrace(true);
  try {
    let traceData;
    
    if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
      traceData = await mockGetTrace(jobId);
    } else {
      const response = await fetch(`${backendUrl}/api/jobs/${jobId}/trace`);
      traceData = await response.json();
    }
    
    setSelectedTrace(traceData);
  } catch (error) {
    console.error('Error loading trace:', error);
  } finally {
    setLoadingTrace(false);
  }
}

// Similar pattern for handleDecision and getImageUrl
```

**Rationale**: HITL page has direct backend calls that need mocking. Keep changes minimal and localized.

---

### 5. Configuration Files

#### .env.mock

```env
# Mock Mode Configuration
NEXT_PUBLIC_DATA_SOURCE=mock
NEXT_PUBLIC_STORAGE_STRATEGY=mock
NEXT_PUBLIC_API_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Firebase config (not used in mock mode, but required by firebase.ts)
NEXT_PUBLIC_FIREBASE_PROJECT_ID=mock-project
NEXT_PUBLIC_FIREBASE_API_KEY=mock-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=mock-domain
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=mock-bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=mock-sender
NEXT_PUBLIC_FIREBASE_APP_ID=mock-app-id
```

**Usage**: Copy to `.env.local` when recording demo, or use via cross-env script.

---

#### package.json

**Change**: Add script under `"scripts"`:

```json
{
  "scripts": {
    "dev": "next dev",
    "dev:mock": "cross-env NEXT_PUBLIC_DATA_SOURCE=mock next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  }
}
```

**Note**: `cross-env` already exists in devDependencies, so this will work on all platforms.

---

## Data Flow Diagrams

### Normal Mode (Production)
```
User submits product
       ↓
  analyze.ts → Backend API → Firestore
       ↓
  useLiveJobs → Firestore subscription → UI update
       ↓
  HITL page → Backend trace API → UI
```

### Mock Mode
```
User submits product
       ↓
  analyze.ts → mockAnalyze() [3s delay]
       ↓                  ↓
  Returns random mock job ← MOCK_JOBS array
       ↓
  useMockLiveJobs → MOCK_JOBS [800ms delay] → UI update
       ↓
  HITL page → mockGetTrace() [1.5s delay] → UI
                          ↓
                  Returns pre-built trace
```

---

## Edge Cases and Error Handling

### 1. Missing Job in Mock Data
**Scenario**: HITL page tries to load a trace for a job not in MOCK_JOBS.
**Handling**: `mockGetTrace` throws an error with a clear message. The UI shows "Trace not found" state.

### 2. Environment Variable Not Set
**Scenario**: User forgets to set `NEXT_PUBLIC_DATA_SOURCE=mock`.
**Handling**: App falls back to production mode seamlessly (default behavior).

### 3. Mock Mode in Production Build
**Scenario**: Someone accidentally deploys with mock mode enabled.
**Handling**: Environment variable should be excluded from production .env files. Add deployment checklist to prevent this.

### 4. Type Mismatches
**Scenario**: MockJob interface doesn't match AnalysisResult exactly.
**Handling**: Use type casting with `as unknown as` where needed, but keep interfaces as close as possible.

---

## Testing Strategy

### Manual Testing Checklist

**Mock Mode Activation**:
- [ ] Run `npm run dev:mock` and verify no Firebase errors
- [ ] Verify dashboard loads with 20+ jobs
- [ ] Verify initial 800ms loading state works

**Product Analysis Flow**:
- [ ] Submit a product and verify 3-4s delay
- [ ] Verify result shows risk score, reasoning, signals
- [ ] Verify result includes policy citations and trace

**HITL Flow**:
- [ ] Open `/hitl` and verify ~5 pending jobs appear
- [ ] Click a job and verify trace loads with 1.5s delay
- [ ] Verify trace shows 4-5 checkpoints
- [ ] Submit a decision and verify success

**Mode Switching**:
- [ ] Stop server, remove mock variable, restart
- [ ] Verify app attempts Firebase connection (error is expected if not configured)
- [ ] Verify no mock-related console logs appear

**Production Build**:
- [ ] Run `npm run build` without mock variable
- [ ] Inspect bundle with `next analyze` (if available)
- [ ] Verify no mock code in production chunks

---

## Performance Considerations

### Build-Time Optimizations
- Mock imports only occur behind `if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock')` checks
- Next.js will tree-shake these imports in production builds
- MOCK_JOBS array (~20KB) is not included in production bundles

### Runtime Performance
- Mock mode has zero performance impact when disabled (checks are compile-time constant)
- When enabled, all delays are simulated (no real network calls = faster overall)
- No memory leaks from timers (all cleaned up in useEffect returns)

---

## Security Considerations

### Data Exposure
- Mock jobs contain no real user data
- All product descriptions and images are fictional or from public sources
- No API keys or credentials in mock files

### Production Isolation
- Mock mode cannot be accidentally activated in production (env var check)
- No mock imports in production bundles
- No shared state between mock and production code

---

## Future Enhancements (Out of Scope)

1. **Interactive Mock Mode**: Allow clicking buttons to trigger specific mock scenarios
2. **Mock Data Editor**: UI for editing mock jobs without touching code
3. **Recording Mode**: Record real sessions and convert to mock data
4. **Playback Mode**: Replay recorded sessions with exact timing
5. **Mock State Persistence**: Save mock state to localStorage between refreshes
6. **Multiple Mock Datasets**: Switch between different mock scenarios (fraud-heavy, approve-heavy, etc.)

---

## Success Metrics

The design is successful if:

1. **Code Impact**: Less than 50 lines of modifications to existing files
2. **Activation Time**: Developer can activate mock mode in under 1 minute
3. **Demo Quality**: Recorded demo looks indistinguishable from production (to non-technical viewers)
4. **Reversibility**: Switching back to production takes 0 code changes (just env var)
5. **Maintenance**: Adding a new mock job requires only editing mockData.ts
