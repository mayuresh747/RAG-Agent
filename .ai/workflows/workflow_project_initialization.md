# Project Initialization Workflow

## Overview
This workflow defines the standard process for initializing a new project or major component within the workspace. It ensures consistent setup, proper documentation, and alignment with project standards from the start.

## Trigger Conditions
- User command: "Initialize new project" or "Start new component"
- New repository cloned without existing structure
- Major refactoring requiring fresh organization

## Preconditions
1. Access to the target project directory
2. User has provided project name/purpose
3. Required tooling is available (git, package managers, etc.)

## Workflow Steps

### Phase 1: Discovery
**Objective:** Understand the project context and requirements

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 1.1 | Gather project requirements from user | Project Manager | Requirements summary |
| 1.2 | Identify technology stack | Project Manager | Tech stack specification |
| 1.3 | Determine project type (web app, API, library, etc.) | Project Manager | Project classification |
| 1.4 | Assess existing assets to preserve | Project Manager | Asset inventory |

### Phase 2: Structure Setup
**Objective:** Create the foundational directory structure

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 2.1 | Create base directory structure | Project Manager | Directory tree |
| 2.2 | Initialize version control (git) | Project Manager | .git directory |
| 2.3 | Create .gitignore with appropriate rules | Project Manager | .gitignore file |
| 2.4 | Set up configuration files | Project Manager | Config files |
| 2.5 | Create .env and .env.example | Project Manager | .env files |

### Phase 3: Documentation Bootstrap
**Objective:** Establish initial documentation

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 3.1 | Create README.md with project overview | Documentation Specialist | README.md |
| 3.2 | Create CONTRIBUTING.md | Documentation Specialist | CONTRIBUTING.md |
| 3.3 | Initialize docs/ directory structure | Documentation Specialist | docs/ structure |
| 3.4 | Create initial architecture decision record | Documentation Specialist | ADR-001 |

### Phase 4: Development Environment
**Objective:** Configure development tooling

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 4.1 | Create virtual environment (e.g., `python -m venv venv`) | Project Manager | Virtual env active |
| 4.2 | Initialize package manager (npm, pip, etc.) | Project Manager | package.json / requirements.txt |
| 4.3 | Set up linting and formatting | Project Manager | Linter config |
| 4.4 | Configure pre-commit hooks (optional) | Project Manager | .pre-commit-config |
| 4.5 | Create development scripts | Project Manager | npm scripts / Makefile |

### Phase 5: Validation
**Objective:** Verify initialization completeness

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 5.1 | Run validation checks | Project Manager | Validation report |
| 5.2 | Verify all required files exist | Project Manager | Checklist |
| 5.3 | Test development environment | Project Manager | Test results |
| 5.4 | Create initial commit | Project Manager | Git commit |

## Decision Points

### DP1: Technology Stack Selection
```
IF user specifies technology → Use specified stack
ELSE IF similar project exists → Suggest matching stack
ELSE → Present options and await user decision
```

### DP2: Documentation Level
```
IF project is public/shared → Full documentation suite
ELSE IF project is prototype → Minimal README only
ELSE → Standard documentation set
```

### DP3: CI/CD Setup
```
IF user requests CI/CD → Include workflow files
ELSE → Skip CI/CD setup (can be added later)
```

## Standard Directory Template

```
project-root/
├── .ai/
│   ├── agents/           # Agent definitions
│   └── workflows/        # Workflow definitions
├── .github/              # GitHub-specific files (if applicable)
│   └── workflows/        # CI/CD workflows
├── docs/
│   ├── architecture/     # Architecture documents
│   ├── guides/           # User guides
│   └── decisions/        # ADRs
├── src/                  # Source code
├── tests/                # Test files
├── scripts/              # Utility scripts
├── .gitignore
├── README.md
├── CONTRIBUTING.md
└── LICENSE               # If open source
```

## Failure Recovery

| Error | Recovery Action |
|-------|-----------------|
| Directory already exists | Ask user: Merge, Overwrite, or Cancel |
| Missing permissions | Report error with required permissions |
| Git init fails | Check git installation → Retry or skip |
| Package manager unavailable | Proceed without → Document manual setup |

## Success Criteria
- [ ] All Phase steps completed or intentionally skipped
- [ ] README.md exists and contains project overview
- [ ] Version control initialized with initial commit
- [ ] Development environment functional
- [ ] User acknowledges project setup complete

## Post-Initialization
- Hand off to user for development work
- Schedule documentation review after first feature
- Monitor for early structural issues
- **Enforce Structure:** Maintain strict file organization; place new files in `src/`, `tests/`, etc., avoiding root directory clutter.

## Related Workflows
- `workflow_feature_development.md` - For adding new features
- `workflow_documentation_update.md` - For documentation changes
- `workflow_release_preparation.md` - For preparing releases
