# Requirements: Mock Mode for Demo

## Overview
Implement a mock data mode for the frontend that allows recording video demos without requiring Firebase or backend connections. The system must be activated via a single environment variable (`NEXT_PUBLIC_DATA_SOURCE=mock`) and should simulate all real behaviors including live feeds, analysis polling, and HITL workflows.

## Core Requirements

### REQ-1: Zero-Touch Production Code
**Priority**: Critical  
**Description**: The mock mode must be implemented as an interception layer that wraps existing data sources without modifying production component code.

**Acceptance Criteria**:
- No changes to UI components (page.tsx, hitl/page.tsx)
- Only minimal modifications (3-5 lines) to data source files (useLiveJobs.ts, analyze.ts, firebase.ts)
- All modifications use environment variable checks: `process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock'`

**Validation**:
- Setting `NEXT_PUBLIC_DATA_SOURCE=prod` or removing the variable reverts to full production behavior
- No mock-related code executes when the variable is not set to 'mock'

---

### REQ-2: Complete Job Dataset
**Priority**: Critical  
**Description**: Provide 20+ pre-defined mock jobs covering all decision flows with realistic Argentine e-commerce data (2026 ARS prices).

**Acceptance Criteria**:
- ~8 APPROVE cases: legitimate products with low risk scores
- ~7 BLOCK cases: clear policy violations or fraud signals
- ~5 HUMAN_REVIEW cases: ambiguous scenarios requiring human judgment
- Each job includes:
  - Complete product metadata (title, description, price)
  - Risk analysis (risk_score, uncertainty, signals, reasoning)
  - Policy data (citations, violations, risk_breakdown)
  - Visual features (extracted features object)
  - Forensic trace (4-5 checkpoints showing agent execution path)
  - Timestamps (varied, simulating historical data)

**Validation**:
- All 20+ jobs render correctly in the dashboard
- HITL view shows ~5 jobs in "Pending Human Review" status
- Each job has a complete trace accessible in the forensic panel

---

### REQ-3: Mock Firestore Hook
**Priority**: Critical  
**Description**: Replace the real-time Firestore subscription (`useLiveJobs`) with a mock hook that returns static data with simulated loading states.

**Acceptance Criteria**:
- `useMockLiveJobs` hook matches the interface of `useLiveJobs`:
  ```typescript
  { jobs: Job[], loading: boolean, error: Error | null }
  ```
- Simulates initial loading state (800ms) before returning data
- Returns jobs sorted by `last_update` descending (newest first)
- Optional: can simulate progressive job arrival for live feed effect

**Validation**:
- Dashboard shows loading skeleton for 800ms, then displays jobs
- Jobs appear in correct order (most recent first)
- No Firestore connection errors in console

---

### REQ-4: Mock Backend API Handlers
**Priority**: Critical  
**Description**: Intercept all backend API calls with mock handlers that simulate delays and return realistic responses.

**Acceptance Criteria**:
- **mockUpload**: Returns a fake `job_id` instantly (no actual upload)
- **mockAnalyze**: Simulates 3-4 second analysis delay, returns a random job from the mock dataset
- **mockGetTrace**: Returns the pre-defined trace for a given job_id
- **mockSubmitDecision**: Returns `{ ok: true }` and logs the decision

**Validation**:
- Submitting a product shows analysis spinner for 3-4 seconds
- Result appears with correct risk assessment and reasoning
- HITL forensic panel loads traces successfully
- Decision submission works without errors

---

### REQ-5: Single Environment Variable Activation
**Priority**: Critical  
**Description**: Mock mode must be controlled by a single environment variable with no other configuration required.

**Acceptance Criteria**:
- Setting `NEXT_PUBLIC_DATA_SOURCE=mock` activates all mocks
- Setting `NEXT_PUBLIC_DATA_SOURCE=prod` (or removing the variable) uses real services
- No code changes needed to switch between modes
- Works in both development (`npm run dev:mock`) and build modes

**Validation**:
- Running `npm run dev:mock` starts app in mock mode
- Running `npm run dev` (without variable) uses real Firebase/backend
- No leftover mock behavior when variable is unset

---

### REQ-6: Realistic Timing Simulation
**Priority**: High  
**Description**: Mock handlers must simulate realistic network and processing delays to create a believable demo experience.

**Acceptance Criteria**:
- Upload: instant (0ms) — simulating local upload
- Analysis: 3-4 seconds — simulating agent processing
- Trace loading: 1-2 seconds — simulating Firestore query
- Decision submission: 500ms — simulating API roundtrip
- Initial job list load: 800ms — simulating Firestore subscription

**Validation**:
- Demo feels natural with appropriate pauses
- No instant responses that break immersion
- Timing is consistent across multiple operations

---

### REQ-7: Image URL Handling
**Priority**: Medium  
**Description**: Mock jobs must reference product images without requiring actual image uploads or storage.

**Acceptance Criteria**:
- Some jobs use placeholder images from `/public/mock/` (if available)
- Most jobs use public Unsplash or similar URLs that match product descriptions
- No broken images or 404 errors in demo
- Images load reasonably fast (external URLs)

**Validation**:
- All 20+ jobs display product images correctly
- No console errors about missing images
- Images are visually appropriate for product categories

---

### REQ-8: HITL Workflow Simulation
**Priority**: High  
**Description**: The HITL (Human-in-the-Loop) dashboard must work fully in mock mode, including job selection, trace viewing, and decision submission.

**Acceptance Criteria**:
- HITL dashboard loads with ~5 jobs in "Pending Human Review" status
- Clicking a job loads its forensic trace (with simulated delay)
- Trace displays 4-5 checkpoints with node names, timestamps, and state
- Submitting a decision (Approve/Block) removes job from pending list
- Historical jobs (APPROVE/BLOCK status) appear in the full job list

**Validation**:
- HITL panel shows pending jobs on load
- Trace panel renders correctly with all checkpoints
- Decision buttons work and update UI
- No errors in console during HITL workflow

---

### REQ-9: Dev Script and Documentation
**Priority**: High  
**Description**: Provide an easy way to run the app in mock mode and document the activation process.

**Acceptance Criteria**:
- Add `dev:mock` script to package.json using cross-env:
  ```json
  "dev:mock": "cross-env NEXT_PUBLIC_DATA_SOURCE=mock next dev"
  ```
- Create `.env.mock` file with required variables
- Document in README or separate doc how to activate mock mode
- Include instructions for Windows (PowerShell) users

**Validation**:
- Running `npm run dev:mock` starts app in mock mode
- Instructions are clear and work on first try
- Script works on both Windows and Unix systems (via cross-env)

---

### REQ-10: Production Safety
**Priority**: Critical  
**Description**: Mock mode must be completely disabled in production builds and have no impact on production performance or bundle size.

**Acceptance Criteria**:
- Mock code tree-shaken out of production builds
- No mock imports in production bundles
- Environment variable checks prevent accidental mock activation in production
- No performance overhead when mock mode is off

**Validation**:
- Production build analysis shows no mock code in bundles
- `process.env.NEXT_PUBLIC_DATA_SOURCE` is properly inlined at build time
- No mock-related console logs in production
- Production deployment works identically to before

---

## Non-Functional Requirements

### NFR-1: Type Safety
- All mock data must conform to existing TypeScript interfaces
- No `any` types in mock implementations
- Mock functions must match real function signatures exactly

### NFR-2: Maintainability
- Mock data centralized in a single file (`mockData.ts`)
- Clear separation between mock and production code
- Easy to add new mock jobs without code changes

### NFR-3: Demo Quality
- Mock data must be realistic and professionally formatted
- Spanish language for Argentine market
- Varied scenarios that showcase all system capabilities
- Visually appealing product images and descriptions

---

## Out of Scope

- Generating actual images for mock products (use public URLs instead)
- Persistent state across page reloads in mock mode
- Admin interface for editing mock data
- Recording or playback of demo sessions
- Simulating concurrent users or load testing

---

## Success Criteria

The mock mode implementation is successful when:

1. A developer can run `npm run dev:mock` and record a complete video demo showing:
   - Product submission with analysis
   - Dashboard showing job history
   - HITL panel with pending reviews
   - Forensic trace exploration
   - Decision submission

2. Switching back to production mode (`npm run dev`) works without any code changes

3. All 20+ mock jobs display correctly with appropriate images, risk scores, and traces

4. No Firebase or backend connection errors appear in mock mode

5. The demo looks professional and realistic enough for portfolio/client presentations
