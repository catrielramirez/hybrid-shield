# Tasks: Mock Mode Implementation

## Task 1: Complete Mock Data File
**Status**: not_started  
**Dependencies**: none  
**Priority**: critical

### Description
Complete the `mockData.ts` file with all remaining mock jobs and ensure data quality.

### Sub-tasks
1. Finish the incomplete BLOCK cases (job-block-004 through job-block-007)
2. Add all 5 HUMAN_REVIEW cases (job-review-001 through job-review-005)
3. Verify all jobs have complete fields (no missing required properties)
4. Ensure timestamps are varied and realistic
5. Verify all image URLs are valid (Unsplash or placeholders)

### Acceptance Criteria
- File exports exactly 20 MockJob objects in MOCK_JOBS array
- Distribution: 8 APPROVE, 7 BLOCK, 5 HUMAN_REVIEW
- All jobs validate against MockJob interface (no TypeScript errors)
- All image_url fields point to accessible images
- Timestamps span last 48 hours with variety

### Verification
```bash
cd frontend
npm run build  # Should succeed with no type errors
```

---

## Task 2: Create useMockLiveJobs Hook
**Status**: not_started  
**Dependencies**: Task 1  
**Priority**: critical

### Description
Implement the mock version of useLiveJobs that returns static data with simulated loading.

### Sub-tasks
1. Create `frontend/lib/mock/useMockLiveJobs.ts`
2. Import MOCK_JOBS from mockData.ts
3. Implement loading state (800ms delay)
4. Return jobs in correct interface format
5. Add TypeScript types matching useLiveJobs

### Acceptance Criteria
- Hook matches useLiveJobs interface exactly
- Returns `{ jobs: Job[], loading: boolean, error: Error | null }`
- Shows loading=true for 800ms before returning data
- No TypeScript errors
- Jobs returned in correct order (newest first by last_update)

### Verification
```typescript
import { useMockLiveJobs } from '@/lib/mock/useMockLiveJobs';

// Should compile and work
const { jobs, loading, error } = useMockLiveJobs();
```

---

## Task 3: Create Mock API Handlers
**Status**: not_started  
**Dependencies**: Task 1  
**Priority**: critical

### Description
Implement all backend API mocking functions with realistic delays.

### Sub-tasks
1. Create `frontend/lib/mock/mockApiHandlers.ts`
2. Implement mockUpload (instant response)
3. Implement mockAnalyze (3-4s delay, returns random interesting job)
4. Implement mockGetTrace (1.5s delay, returns job's trace)
5. Implement mockSubmitDecision (500ms delay, logs and returns success)
6. Implement mockGetImageUrl (instant, returns job's image_url)

### Acceptance Criteria
- All functions return Promises
- Delays match specification (see sub-tasks)
- mockAnalyze returns valid AnalysisResult type
- mockGetTrace returns valid trace structure
- mockSubmitDecision logs to console for debugging
- No TypeScript errors

### Verification
```typescript
// Manual test
const result = await mockAnalyze({ thread_id: 'test', ... });
// Should take 3-4 seconds and return a job
```

---

## Task 4: Modify firebase.ts for Mock Mode Flag
**Status**: not_started  
**Dependencies**: none  
**Priority**: critical

### Description
Add the mock mode detection flag export to firebase.ts.

### Sub-tasks
1. Open `frontend/lib/firebase.ts`
2. Add export at the end: `export const isMockMode = process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock';`
3. Verify no other changes needed

### Acceptance Criteria
- Single line added to file
- Export is accessible from other files
- No changes to existing Firebase initialization

### Verification
```typescript
import { isMockMode } from '@/lib/firebase';
console.log('Mock mode:', isMockMode); // Should print true in mock mode
```

---

## Task 5: Modify useLiveJobs Hook for Mock Support
**Status**: not_started  
**Dependencies**: Task 2, Task 4  
**Priority**: critical

### Description
Add mock mode redirection to the useLiveJobs hook.

### Sub-tasks
1. Open `frontend/lib/hooks/useLiveJobs.ts`
2. Import `isMockMode` from firebase.ts
3. Import `useMockLiveJobs` from mock/useMockLiveJobs.ts
4. Add 3-line check at start of function: `if (isMockMode) return useMockLiveJobs();`
5. Verify no changes to rest of function

### Acceptance Criteria
- Exactly 3 new lines added (2 imports, 1 if statement)
- Existing code unchanged
- TypeScript compiles without errors
- Hook returns mock data when NEXT_PUBLIC_DATA_SOURCE=mock

### Verification
```bash
# Start in mock mode
NEXT_PUBLIC_DATA_SOURCE=mock npm run dev
# Open dashboard, should see mock jobs
```

---

## Task 6: Modify analyze.ts for Mock Support
**Status**: not_started  
**Dependencies**: Task 3  
**Priority**: critical

### Description
Add mock mode branch to the analyzeProduct server action.

### Sub-tasks
1. Open `frontend/app/actions/analyze.ts`
2. Import mockAnalyze from mock/mockApiHandlers
3. Add mock mode check at start of analyzeProduct function
4. Return mockAnalyze(params) when in mock mode
5. Verify existing polling logic unchanged

### Acceptance Criteria
- 3-4 new lines added (1 import, 1 if check, 1 return)
- Existing backend polling unchanged
- TypeScript compiles without errors
- Analysis works in mock mode without backend calls

### Verification
```bash
# Start in mock mode
NEXT_PUBLIC_DATA_SOURCE=mock npm run dev
# Submit a product, should see 3-4s delay then mock result
```

---

## Task 7: Modify hitl/page.tsx for Mock Support
**Status**: not_started  
**Dependencies**: Task 3  
**Priority**: high

### Description
Add mock mode handling to all backend API calls in the HITL page.

### Sub-tasks
1. Open `frontend/app/hitl/page.tsx`
2. Import mock handlers: mockGetTrace, mockSubmitDecision, mockGetImageUrl
3. Wrap `handleSelectJob` trace fetch with mock check
4. Wrap `handleDecision` submission with mock check
5. Wrap any image URL fetches with mock check (if applicable)
6. Test all three flows work in mock mode

### Acceptance Criteria
- ~15 lines modified total (import + 3 function wrappers)
- All backend calls check `process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock'` first
- Mock mode bypasses all real API calls
- Production mode unchanged
- TypeScript compiles without errors

### Verification
```bash
# Start in mock mode
NEXT_PUBLIC_DATA_SOURCE=mock npm run dev
# Navigate to /hitl
# Click a pending job -> trace should load
# Submit decision -> should succeed
```

---

## Task 8: Create .env.mock Configuration File
**Status**: not_started  
**Dependencies**: none  
**Priority**: high

### Description
Create the environment configuration file for mock mode.

### Sub-tasks
1. Create `frontend/.env.mock` file
2. Add NEXT_PUBLIC_DATA_SOURCE=mock
3. Add NEXT_PUBLIC_STORAGE_STRATEGY=mock
4. Add mock Firebase config (required but unused)
5. Add placeholder API URLs

### Acceptance Criteria
- File contains all required environment variables
- NEXT_PUBLIC_DATA_SOURCE set to 'mock'
- Firebase config present (even though unused in mock mode)
- No real credentials or sensitive data

### Verification
```bash
cp frontend/.env.mock frontend/.env.local
npm run dev
# App should start in mock mode
```

---

## Task 9: Add dev:mock Script to package.json
**Status**: not_started  
**Dependencies**: none  
**Priority**: high

### Description
Add a convenient npm script to run the app in mock mode.

### Sub-tasks
1. Open `frontend/package.json`
2. Add `"dev:mock": "cross-env NEXT_PUBLIC_DATA_SOURCE=mock next dev"` to scripts
3. Verify cross-env is already in devDependencies (it is)
4. Test script works on Windows and Unix

### Acceptance Criteria
- Script added to package.json
- Uses cross-env for cross-platform compatibility
- Running `npm run dev:mock` starts app in mock mode
- No additional dependencies needed

### Verification
```bash
cd frontend
npm run dev:mock
# Should start with mock mode active
# Check console for no Firebase connection errors
```

---

## Task 10: Verify Mock Mode Functionality
**Status**: not_started  
**Dependencies**: Task 1-9  
**Priority**: critical

### Description
Comprehensive end-to-end testing of mock mode functionality.

### Sub-tasks
1. Start app with `npm run dev:mock`
2. Test dashboard loads with 20+ jobs
3. Test product submission flow (upload + analysis)
4. Test HITL page loads with pending jobs
5. Test trace viewing in HITL
6. Test decision submission in HITL
7. Verify all images load correctly
8. Check console for errors

### Acceptance Criteria
- Dashboard shows all mock jobs correctly
- Product submission works with 3-4s analysis delay
- HITL shows ~5 pending review jobs
- Clicking a job loads its trace (4-5 checkpoints)
- Submitting a decision works without errors
- All product images display (no 404s)
- No console errors during normal operation

### Verification
```bash
npm run dev:mock
# Manual testing checklist:
# [ ] Dashboard loads
# [ ] Submit product works
# [ ] HITL pending jobs visible
# [ ] Trace panel works
# [ ] Decision submission works
# [ ] Images all load
```

---

## Task 11: Test Production Mode Still Works
**Status**: not_started  
**Dependencies**: Task 1-9  
**Priority**: critical

### Description
Verify that production mode is unaffected by mock mode changes.

### Sub-tasks
1. Remove or comment out NEXT_PUBLIC_DATA_SOURCE from .env.local
2. Start app with `npm run dev`
3. Verify it attempts Firebase connection (expected to see connection or auth errors if Firebase not fully configured)
4. Verify no mock-related code runs
5. Verify no mock imports in dev console

### Acceptance Criteria
- App runs without crashing
- No mock-related console logs
- Firebase connection attempted (error is OK if not configured)
- No references to MOCK_JOBS or mock handlers in console

### Verification
```bash
# Remove mock mode variable
npm run dev
# App should attempt real Firebase/backend connections
# No mock-specific behavior should occur
```

---

## Task 12: Create Mock Mode Documentation
**Status**: not_started  
**Dependencies**: Task 1-11  
**Priority**: medium

### Description
Document how to use mock mode for future reference.

### Sub-tasks
1. Create `frontend/MOCK_MODE.md` or add section to existing README
2. Document how to activate mock mode (3 methods: script, .env.local, inline)
3. Document what gets mocked (Firestore, backend API)
4. Document how to add new mock jobs
5. Add troubleshooting section

### Acceptance Criteria
- Clear instructions for activating mock mode
- Examples for all three activation methods
- Explanation of what is/isn't mocked
- Guide for adding new mock jobs to mockData.ts
- At least 3 common troubleshooting scenarios

### Verification
- Have a colleague follow the docs to activate mock mode successfully

---

## Task 13: Verify Production Build Excludes Mock Code
**Status**: not_started  
**Dependencies**: Task 1-11  
**Priority**: medium

### Description
Ensure mock code is tree-shaken out of production builds.

### Sub-tasks
1. Remove NEXT_PUBLIC_DATA_SOURCE from .env (ensure production mode)
2. Run `npm run build`
3. Check build output for mock-related chunks
4. Optionally use bundle analyzer to verify
5. Verify build completes without errors

### Acceptance Criteria
- Build completes successfully
- No mock-related chunks in .next/static
- Build size similar to before mock mode implementation
- No mock imports in production bundles

### Verification
```bash
cd frontend
unset NEXT_PUBLIC_DATA_SOURCE
npm run build
# Check .next/static for mock-related files (should be none)
```

---

## Optional Enhancement Tasks

### Task 14: Add Progressive Job Arrival (Optional)
**Status**: not_started  
**Dependencies**: Task 2  
**Priority**: low

### Description
Enhance mock mode with jobs appearing progressively over time.

### Sub-tasks
1. Modify useMockLiveJobs to start with 10 jobs
2. Add setInterval to add 1 job every 15 seconds
3. Stop adding when all 20 jobs are visible
4. Clean up interval on unmount

### Acceptance Criteria
- Jobs appear gradually during demo
- Mimics real-time feed behavior
- Interval cleaned up properly
- Optional feature (can be disabled)

---

### Task 15: Add Mock Image Placeholders (Optional)
**Status**: not_started  
**Dependencies**: Task 1  
**Priority**: low

### Description
Generate or find placeholder images for mock products.

### Sub-tasks
1. Create `frontend/public/mock/` directory
2. Add 5-10 generic product images
3. Update mockData.ts to reference local images where appropriate
4. Keep some Unsplash URLs for variety

### Acceptance Criteria
- `/public/mock/` contains placeholder images
- Images are appropriate for product categories
- Mix of local and external URLs in mockData
- All images load without errors

---

## Task Execution Order

**Critical Path**:
1. Task 1 (Mock Data)
2. Task 4 (Firebase flag)
3. Task 2 (Mock Hook)
4. Task 3 (Mock Handlers)
5. Task 5 (Modify useLiveJobs)
6. Task 6 (Modify analyze)
7. Task 7 (Modify HITL)
8. Task 8 (.env.mock)
9. Task 9 (package.json script)
10. Task 10 (Verification)
11. Task 11 (Production test)
12. Task 13 (Build verification)

**Parallel Opportunities**:
- Tasks 2 and 3 can be done in parallel after Task 1
- Task 4 can be done anytime (independent)
- Task 8 and 9 can be done anytime (independent)
- Task 12 can be done anytime (documentation)

**Optional**:
- Task 14 and 15 after critical path complete

---

## Estimated Effort

| Task | Estimated Time | Complexity |
|------|----------------|------------|
| Task 1  | 30 min | Medium |
| Task 2  | 10 min | Low |
| Task 3  | 15 min | Low |
| Task 4  | 2 min  | Low |
| Task 5  | 5 min  | Low |
| Task 6  | 5 min  | Low |
| Task 7  | 15 min | Medium |
| Task 8  | 5 min  | Low |
| Task 9  | 2 min  | Low |
| Task 10 | 20 min | Low |
| Task 11 | 10 min | Low |
| Task 12 | 15 min | Low |
| Task 13 | 10 min | Low |

**Total**: ~2.5 hours for critical path  
**With optional**: +1 hour

---

## Risk Mitigation

**Risk**: TypeScript type mismatches between MockJob and AnalysisResult  
**Mitigation**: Use `as unknown as` casting where needed, keep interfaces aligned

**Risk**: Mock images return 404  
**Mitigation**: Use well-known public URLs (Unsplash), test all URLs before committing

**Risk**: Mock mode accidentally enabled in production  
**Mitigation**: Add deployment checklist, use environment-specific .env files

**Risk**: Incomplete mock data causes UI crashes  
**Mitigation**: Task 1 includes verification step, Task 10 tests all flows

**Risk**: Changes break production mode  
**Mitigation**: Task 11 explicitly tests production mode, all changes are additive

---

## Success Criteria

All tasks complete when:

1. Running `npm run dev:mock` shows dashboard with 20+ jobs
2. Submitting a product shows analysis result after 3-4s
3. HITL page shows pending reviews and allows decisions
4. Running `npm run dev` (without mock var) works normally
5. Production build excludes mock code
6. No TypeScript errors in any mode
7. Documentation exists for activating and using mock mode
