# Mock Mode Documentation

## Overview

Mock Mode allows you to run the application without requiring Firebase or backend connections. This is ideal for:
- Recording video demos
- Testing UI without infrastructure
- Local development without cloud dependencies
- Portfolio presentations

## Activation Methods

### Method 1: npm script (Recommended)

```bash
cd frontend
npm run dev:mock
```

This uses the `cross-env` package to set the environment variable cross-platform.

### Method 2: Environment File

1. Copy the mock environment template:
```bash
cp .env.mock .env.local
```

2. Start the development server:
```bash
npm run dev
```

### Method 3: Inline Environment Variable

**Linux/Mac**:
```bash
NEXT_PUBLIC_DATA_SOURCE=mock npm run dev
```

**Windows PowerShell**:
```powershell
$env:NEXT_PUBLIC_DATA_SOURCE="mock"; npm run dev
```

**Windows CMD**:
```cmd
set NEXT_PUBLIC_DATA_SOURCE=mock && npm run dev
```

## What Gets Mocked

When `NEXT_PUBLIC_DATA_SOURCE=mock` is set:

- **Firebase Firestore**: `useLiveJobs` hook returns 20+ pre-defined jobs
- **Backend API**: All `/api/*` calls are intercepted:
  - Product upload: Returns instant fake job_id
  - Analysis: Returns mock results after 3-4s delay
  - Trace fetching: Returns pre-built forensic traces
  - Decision submission: Logs to console and returns success
  - Image URLs: Returns URLs from mock data

## Mock Data

The mock dataset includes 20+ jobs covering three decision flows:

- **~8 APPROVE cases**: Legitimate products with low risk scores
- **~7 BLOCK cases**: Clear policy violations or fraud signals
- **~5 HUMAN_REVIEW cases**: Ambiguous scenarios requiring human judgment

Each job contains:
- Complete product metadata (title, description, price in ARS)
- Risk analysis (score, uncertainty, signals, reasoning)
- Policy data (citations, violations, risk breakdown)
- Visual features (extracted features object)
- Forensic trace (4-5 checkpoints showing agent execution)
- Varied timestamps (simulating historical data over 48 hours)

## Deactivation

To return to production mode:

1. **If using .env.local**: Remove or comment out `NEXT_PUBLIC_DATA_SOURCE`
2. **If using script**: Use `npm run dev` instead of `npm run dev:mock`
3. **If using inline variable**: Just run `npm run dev` without the variable

No code changes are needed to switch between modes.

## Adding New Mock Jobs

To add new mock jobs to the dataset:

1. Open `frontend/lib/mock/mockData.ts`
2. Add a new entry to the `MOCK_JOBS` array:

```typescript
{
  id: "job-custom-001",
  thread_id: "job-custom-001",
  status: "APPROVE", // or "BLOCK" or "PENDING_HUMAN_REVIEW"
  final_action: "Approve", // or "Block" or "Human Review"
  title: "Your Product Title",
  description: "Product description...",
  price: 150000, // ARS
  image_url: "https://your-image-url.com/image.jpg",
  risk_score: 0.15,
  uncertainty: 0.08,
  routing_reason: "auto_approved",
  reasoning: "Explanation of the decision...",
  signals: {
    visual_dissonance: false,
    contact_info_detected: false,
    price_anomaly: false,
    policy_match: false,
  },
  features: {
    primary_object: "Your product type",
    object_category: "Category",
    objects_detected: ["list", "of", "detected", "objects"],
    contact_info_detected: false,
    visual_dissonance: false,
    product_condition: "Nuevo",
    is_sellable: true,
    fraud_signals: [],
    confidence: 0.95,
  },
  created_at: hoursAgo(12), // Use helper function
  last_update: hoursAgo(11.5),
  trace: buildTrace("job-custom-001", "Approve", 0.15), // Auto-generates trace
}
```

3. Save the file - no restart needed in dev mode (hot reload)

## Troubleshooting

### Issue: App still tries to connect to Firebase

**Solution**: Ensure `NEXT_PUBLIC_DATA_SOURCE=mock` is set **before** starting the server. Environment variables are read at build/start time, not runtime.

### Issue: Mock images don't load (404 errors)

**Solution**: Mock jobs use public URLs (Unsplash) and some local placeholders. Ensure:
- You have internet connection (for external URLs)
- Local images exist in `/public/mock/` (if referenced)

### Issue: Types don't match between MockJob and AnalysisResult

**Solution**: The mock system uses type casting (`as unknown as`) where needed. If you add new fields to `AnalysisResult`, add them to `MockJob` interface as well.

### Issue: Mock mode works but production mode fails

**Solution**: This is expected if Firebase isn't configured. To test production mode:
1. Set up Firebase credentials in `.env.local`
2. Ensure backend is running
3. Remove `NEXT_PUBLIC_DATA_SOURCE` variable

### Issue: Changes to mock data don't appear

**Solution**: 
- In dev mode: Save the file and refresh the browser (hot reload should work)
- In build mode: Rebuild with `npm run build`
- Clear browser cache if needed

### Issue: TypeScript errors in mock files

**Solution**:
- Run `npm run build` to see all type errors
- Ensure all MockJob objects have required fields
- Check that image_url paths are strings
- Verify trace arrays have correct structure

## File Modifications Summary

Mock mode required minimal changes to existing code:

1. **lib/firebase.ts**: Added 1 line (export `isMockMode` flag)
2. **lib/hooks/useLiveJobs.ts**: Added 3 lines (import mock hook, redirect in mock mode)
3. **app/actions/analyze.ts**: Added 4 lines (import mock handler, check mode, call mock)
4. **app/hitl/page.tsx**: Modified 3 functions (~20 lines total) to check mock mode

All changes use environment variable checks that get optimized away in production builds.

## Performance Notes

- **Development**: Mock mode is slightly faster (no network calls)
- **Production**: Zero overhead - mock code is tree-shaken out of builds
- **Bundle Size**: No increase in production bundles (dead code elimination)

## Demo Recording Tips

When recording demos in mock mode:

1. Use `npm run dev:mock` for consistent behavior
2. Refresh the page before starting recording (ensures clean state)
3. The dashboard loads jobs after 800ms (wait for this)
4. Product analysis takes 3-4 seconds (natural demo timing)
5. HITL trace loading takes 1-2 seconds (adds realism)
6. Have ~5 jobs in "Pending Human Review" status for HITL demos

## Production Deployment

**IMPORTANT**: Never deploy with `NEXT_PUBLIC_DATA_SOURCE=mock` set.

Deployment checklist:
- [ ] Remove `NEXT_PUBLIC_DATA_SOURCE` from production `.env` files
- [ ] Verify `npm run build` succeeds without mock variable
- [ ] Test deployed app connects to real Firebase/backend
- [ ] Check console has no "[MOCK]" log messages

Mock mode is designed for local development and demos only.
