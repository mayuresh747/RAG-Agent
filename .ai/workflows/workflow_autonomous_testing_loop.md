# Autonomous Testing Loop Workflow

## Overview
This workflow defines the cyclical process of Designing, Scripting, Executing, and Repairing tests. It enables the system to autonomously improve quality by iterating on failures until a passing state is achieved (or max retries reached).

## Trigger Conditions
- New Feature Implementation Complete (Gate 3 of Secure Delivery)
- Bug Fix applied
- Manual "Run Tests" command
- Scheduled nightly regression

## Preconditions
1. Code is implemented and theoretically ready
2. Testing Agents are installed

## Agents Involved
1. **Test Architect** (Planner)
2. **QA Automation Engineer** (Scripter)
3. **Test Executor** (Runner)
4. **Implementation Specialist** (Fixer - borrowed from Secure Delivery)

## Workflow Diagram

```
      Start
        │
        ▼
┌───────────────┐
│ Test Architect│  <─── (Analyze Implementation)
│ (Design Plan) │
└───────┬───────┘
        │
        ▼
┌──────────────────┐
│ QA Engineer      │  <─── (Write/Update Scripts)
│ (Generate Code)  │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐     PASS
│ Test Executor    │ ───────────────▶ ✅ SUCCESS
│ (Run Suite)      │
└───────┬──────────┘
        │ FAIL
        │
        ▼
┌──────────────────┐
│ Analysis &       │
│ Repair Loop      │
└───────┬──────────┘
        │
   (Fix Code or Test)
        │
        └──────────▶ Loop Back to Execution
                     (Max 3 Iterations)
```

## Step-by-Step Execution

### Phase 1: Preparation (Design & Script)
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 1.1 | Analyze changes | Test Architect | Test Plan |
| 1.2 | Generate/Update scripts | QA Engineer | .spec files |
| 1.3 | Prepare environment | Test Executor | Ready state |

### Phase 2: Execution
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 2.1 | Run Test Suite | Test Executor | Logs/Results |
| 2.2 | Analyze Result | Test Executor | Pass/Fail |

**BRANCH:**
- IF **PASS**: Workflow Ends (Success)
- IF **FAIL**: Proceed to Phase 3

### Phase 3: Analysis & Repair (The Loop)
*Iteration Limit: 3 Attempts*

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 3.1 | Analyze Failure Log | QA Engineer | Root Cause |
| 3.2 | Determine Fix Type | QA Engineer | "Fix Code" or "Fix Test" |
| 3.3a | IF Fix Code | Implementation Specialist | Updated Source |
| 3.3b | IF Fix Test | QA Engineer | Updated Script |
| 3.4 | Re-Run Tests | Test Executor | New Result |

### Phase 4: Final Outcome
- **Success:** Tests pass within limit.
- **Failure:** Tests still fail after 3 loops. Manual intervention requested.

## Decision Points

### DP1: Fix Strategy
```
IF Error == "AssertionError" AND Impl matches Spec → Fix Implementation
IF Error == "SelectorNotFound" AND DOM changed → Fix Test
IF Error == "Timeout" → Optimize or Fix Performance
```

### DP2: Loop Safety
```
IF Iteration > 3 → STOP (Prevent infinite loop)
IF Error == "Environment Crash" → STOP (System issue)
```

## Failure Recovery
- **Infinite Loop:** Hard stop at 3 retries.
- **Environment Down:** Executor detects pre-flight failure, aborts loop.
- **Agent Confusion:** If Fix Type is ambiguous, ask User.

## Phase 5: Final Proof of Work (MANDATORY)
Before finishing, you MUST populate this table to prove the loop is complete and successful:

| Item | Status | Details | Verified? |
|------|--------|---------|-----------|
| Test Plan | [Created/Updated] | path/to/test_plan.md | [ ] |
| Test Scripts | [Generated] | path/to/scripts/ | [ ] |
| Execution Log | [Analyzed] | Run ID / Timestamp | [ ] |
| Final Result | [PASS/FAIL] | Success rate % | [ ] |

**Rule:** If Final Result is FAIL, you cannot mark this workflow as success unless max retries (3) were exhausted.

## Success Criteria
- [ ] Test Plan created/updated
- [ ] Scripts generated
- [ ] Tests executed
- [ ] Failures automatically analyzed and repaired (if possible)
- [ ] Final green state achieved

## Related Agents
- [Test Architect](../agents/agent_test_architect.md)
- [QA Automation Engineer](../agents/agent_qa_automation_engineer.md)
- [Test Executor](../agents/agent_test_executor.md)
