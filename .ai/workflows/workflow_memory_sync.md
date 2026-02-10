# Context Synchronization Workflow

## Overview
This workflow ensures project state and documentation stay synchronized. It orchestrates the Memory Keeper and Documentation Updater agents to maintain consistency across sessions.

## Trigger Conditions
- Session start (load context)
- Significant project event (update state)
- Feature completion (sync docs)
- Manual trigger (force sync)

## Preconditions
1. `.ai/memory/project_memory.json` exists
2. Memory Keeper agent is installed
3. Documentation Updater agent is installed

## Agents Involved
1. **Memory Keeper** — Reads/writes project state
2. **Documentation Updater** — Syncs documentation with state

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     TRIGGER EVENT                            │
│  (Session Start / Feature Change / Manual Sync / Commit)    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY KEEPER                             │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Load State   │───▶│ Process      │───▶│ Save State   │  │
│  │              │    │ Changes      │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  Output: Updated project_memory.json                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               DOCUMENTATION UPDATER                          │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Read State   │───▶│ Generate     │───▶│ Update Docs  │  │
│  │              │    │ Content      │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  Output: Updated README.md, CHANGELOG.md                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SYNC COMPLETE                             │
│           Project state and docs are consistent             │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Execution

### Phase 1: State Loading
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 1.1 | Load project_memory.json | Memory Keeper | State object |
| 1.2 | Validate state integrity | Memory Keeper | Validation result |
| 1.3 | Initialize if missing | Memory Keeper | New state (if needed) |

### Phase 2: State Update (if triggered by event)
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 2.1 | Identify changes | Memory Keeper | Change list |
| 2.2 | Update state object | Memory Keeper | Modified state |
| 2.3 | Append to history_log | Memory Keeper | Log entry |
| 2.4 | Write to disk | Memory Keeper | Persisted JSON |
| 2.5 | Update history.md | Memory Keeper | Persisted markdown |

### Phase 3: Documentation Sync
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 3.1 | Read current state | Documentation Updater | State data |
| 3.2 | Compare with docs | Documentation Updater | Diff report |
| 3.3 | Generate updates | Documentation Updater | New content |
| 3.4 | Apply to README | Documentation Updater | Updated README |
| 3.5 | Update CHANGELOG | Documentation Updater | Updated CHANGELOG |

### Phase 4: Verification
| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 4.1 | Verify state saved | Memory Keeper | Confirmation |
| 4.2 | Verify docs updated | Documentation Updater | Confirmation |
| 4.3 | Log sync completion | Memory Keeper | History entry |

## Sync Triggers

| Event | Sync Type | Scope |
|-------|-----------|-------|
| Session start | Load | State only |
| Feature started | Update | State + history |
| Feature completed | Full | State + docs + changelog |
| ADR added | Update | State + docs |
| Before commit | Full | All files |
| Manual request | Full | All files |

## State File Locations

```
.ai/memory/
├── project_memory.json    # Structured state (JSON)
└── history.md             # Human-readable history
```

## Decision Points

### DP1: State Validation
```
IF state file exists AND is valid JSON → Load state
ELSE IF state file corrupted → Attempt recovery from history.md
ELSE → Initialize new state
```

### DP2: Doc Sync Scope
```
IF minor change (status update) → Update README only
IF major change (feature complete) → Update README + CHANGELOG
IF architecture change → Update README + CHANGELOG + ADR index
```

### DP3: Conflict Resolution
```
IF state conflicts with docs → State is source of truth
IF custom doc content exists → Preserve custom content
IF merge conflict → Flag for manual review
```

## Failure Recovery

| Failure | Recovery |
|---------|----------|
| State file missing | Initialize new state |
| State file corrupted | Rebuild from history.md |
| Doc update fails | Log error, retry on next sync |
| Disk write error | Alert user, keep state in memory |

## Phase 5: Final Proof of Work (MANDATORY)
Before finishing, you MUST run `ls -l` on the memory files and populate this table:

| File | Status | Last Modified (Time) | verified? |
|------|--------|----------------------|-----------|
| `.ai/memory/project_memory.json` | [Updated/Skipped] | [Time] | [ ] |
| `.ai/memory/history.md` | [Updated/Skipped] | [Time] | [ ] |
| `CHANGELOG.md` | [Updated/Skipped] | [Time] | [ ] |
| `README.md` | [Updated/Skipped] | [Time] | [ ] |

**Rule:** If any "Updated" file has a timestamp older than 1 minute, the sync FAILED. Retry immediately.

## Success Criteria
- [ ] State loaded/saved successfully
- [ ] History log updated
- [ ] Documentation synchronized
- [ ] No data loss
- [ ] Sync completed in < 5 seconds

## Related Files
- [Memory Keeper Agent](../agents/agent_memory_keeper.md)
- [Documentation Updater Agent](../agents/agent_documentation_updater.md)
- [project_memory.json](../memory/project_memory.json)
- [history.md](../memory/history.md)
