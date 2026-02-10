# Secure Feature Delivery Workflow

## Overview
This workflow enforces a "Measure Twice, Cut Once" approach to feature development. No code is written until feasibility is confirmed and dependencies are mapped. This prevents wasted effort and reduces regressions.

## Trigger Conditions
- User requests a new feature
- Bug fix requires code changes
- Refactoring is proposed
- Any modification to existing functionality

## Preconditions
1. Feature request is defined (even roughly)
2. Agent system is installed and available
3. Project codebase is accessible

## Agents Involved
1. **Feasibility Analyst** — Validates feasibility, produces Feasibility Report
2. **Dependency Manager** — Maps impact, produces Dependency Map
3. **Implementation Specialist** — Writes code after approval

## Workflow Diagram

```
┌──────────────────┐
│  Feature Request │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────┐
│ Feasibility      │────▶│  Feasibility Report │
│ Analyst          │     │  (PROCEED/HOLD/     │
└────────┬─────────┘     │   REVISE/REJECT)    │
         │               └─────────────────────┘
         │
    ┌────┴────┐
    │ PROCEED?│
    └────┬────┘
         │ YES
         ▼
┌──────────────────┐     ┌─────────────────────┐
│ Dependency       │────▶│   Dependency Map    │
│ Manager          │     │   (Files, Order,    │
└────────┬─────────┘     │    Risk Level)      │
         │               └─────────────────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────┐
│ Implementation   │────▶│   Source Code       │
│ Specialist       │     │   + Tests           │
└────────┬─────────┘     └─────────────────────┘
         │
         ▼
┌──────────────────┐
│   Verification   │
│   & Commit       │
└──────────────────┘
```

## Step-by-Step Execution

### Gate 1: Feasibility Analysis
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 1.1 | Receive feature request | Project Manager | Scoped request |
| 1.2 | Analyze requirements | Feasibility Analyst | Requirements doc |
| 1.3 | Assess technical feasibility | Feasibility Analyst | Technical assessment |
| 1.4 | Identify risks | Feasibility Analyst | Risk list |
| 1.5 | Generate Feasibility Report | Feasibility Analyst | **Feasibility Report** |

**GATE DECISION:**
```
IF Feasibility Report = PROCEED → Continue to Gate 2
IF Feasibility Report = CONDITIONAL → Continue with caution flags
IF Feasibility Report = HOLD → Wait for user clarification
IF Feasibility Report = REVISE → Return to user for scope changes
IF Feasibility Report = REJECT → End workflow, report reason
```

### Gate 2: Dependency Mapping
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 2.1 | Analyze codebase structure | Dependency Manager | File tree |
| 2.2 | Trace affected components | Dependency Manager | Impact list |
| 2.3 | Check external dependencies | Dependency Manager | Package audit |
| 2.4 | Determine change order | Dependency Manager | Sequence plan |
| 2.5 | Generate Dependency Map | Dependency Manager | **Dependency Map** |

**GATE DECISION:**
```
IF Risk Level = LOW/MEDIUM → Proceed to Implementation
IF Risk Level = HIGH → Require user acknowledgment
IF Risk Level = CRITICAL → Require explicit approval + backup plan
IF Breaking Changes detected → Block until migration plan exists
```

### Gate 3: Implementation
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 3.1 | Review Feasibility Report | Implementation Specialist | Understanding |
| 3.2 | Review Dependency Map | Implementation Specialist | Change plan |
| 3.3 | Implement code changes | Implementation Specialist | Source code |
| 3.4 | Write/update tests | Implementation Specialist | Test files |
| 3.5 | Run quality checks | Implementation Specialist | Lint/test results |

### Gate 4: Verification
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 4.1 | Verify all tests pass | Project Manager | Test report |
| 4.2 | Confirm linting passes | Project Manager | Lint report |
| 4.3 | Review documentation | Documentation Specialist | Doc updates |
| 4.4 | Create commit | Project Manager | Git commit |

## Decision Matrix

| Feasibility | Dependency Risk | Action |
|-------------|-----------------|--------|
| PROCEED | LOW | Implement immediately |
| PROCEED | MEDIUM | Implement with review |
| PROCEED | HIGH | Implement in phases |
| PROCEED | CRITICAL | Require approval + backup |
| CONDITIONAL | Any | Extra testing required |
| HOLD | Any | Pause for clarification |
| REVISE | Any | Return to planning |
| REJECT | Any | End workflow |

## Failure Recovery

| Failure Point | Recovery Action |
|---------------|-----------------|
| Feasibility unclear | Request more context from user |
| Dependencies circular | Flag and request architecture review |
| Implementation blocked | Return to Dependency Manager for alternatives |
| Tests fail | Fix code or revise scope |
| Quality gate fails | Address issues before proceeding |

## State Transitions
```
idle → analyzing_feasibility → mapping_dependencies → implementing → verifying → complete
                ↓                      ↓                    ↓
              hold/revise/reject    blocked              fix_issues
```

## Phase 5: Final Proof of Work (MANDATORY)
Before finishing, you MUST populate this table with findings from your verification phase:

| Artifact | Status | Location/Command | Verified? |
|----------|--------|------------------|-----------|
| Feasibility Report | [Created] | path/to/report.md | [ ] |
| Dependency Map | [Created] | path/to/map.md | [ ] |
| Implementation | [Completed] | Files modified | [ ] |
| Test Results | [Passed] | Command output | [ ] |
| Documentation | [Updated] | README/CHANGELOG | [ ] |

**Rule:** You must visually confirm (via `ls`, `grep`, or `test` runs) that all artifacts exist and state matches reality.

## Success Criteria
- [ ] Feasibility Report approved
- [ ] Dependency Map created with acceptable risk
- [ ] Code implemented following change order
- [ ] All tests pass
- [ ] Linting passes
- [ ] Documentation updated
- [ ] Commit created with descriptive message

## Related Agents
- [Feasibility Analyst](../agents/agent_feasibility_analyst.md)
- [Dependency Manager](../agents/agent_dependency_manager.md)
- [Implementation Specialist](../agents/agent_implementation_specialist.md)
