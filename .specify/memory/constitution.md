
<!--
Sync Impact Report:
Version change: (none) → 1.0.0
List of modified principles: All placeholders filled with initial values
Added sections: None (all template sections now concrete)
Removed sections: None
Templates requiring updates: plan-template.md (✅ updated), spec-template.md (✅ updated), tasks-template.md (✅ updated)
Follow-up TODOs: RATIFICATION_DATE (needs project owner input)
-->

# AgentMatt Constitution


## Core Principles

### I. Library-First
Every feature starts as a standalone library. Libraries must be self-contained, independently testable, and documented. Each library must have a clear purpose—organizational-only libraries are not permitted.

### II. CLI Interface
Every library exposes functionality via a CLI. Text in/out protocol: stdin/args → stdout, errors → stderr. Support both JSON and human-readable formats.

### III. Test-First (NON-NEGOTIABLE)
TDD is mandatory: Tests are written and user-approved before implementation. Red-Green-Refactor cycle is strictly enforced.

### IV. Integration Testing
Integration tests are required for new library contracts, contract changes, inter-service communication, and shared schemas.

### V. Observability & Simplicity
Text I/O ensures debuggability. Structured logging is required. Start simple and follow YAGNI (You Aren't Gonna Need It) principles.


## Additional Constraints

All code must comply with the approved technology stack. Security best practices and performance standards must be followed. Deployment must use approved CI/CD pipelines.


## Development Workflow

All code changes require code review and must pass all tests before merging. Deployment requires approval from at least one maintainer. Quality gates include passing all tests, code review, and compliance with this constitution.


## Governance

This constitution supersedes all other practices. Amendments require documentation, approval by project maintainers, and a migration plan if needed. All PRs and reviews must verify compliance with these principles. Complexity must be justified. Use runtime development guidance as referenced in project documentation.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): Project owner to supply | **Last Amended**: 2026-02-13
