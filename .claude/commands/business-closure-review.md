# business-closure-review

Review the current project for business logic closure — whether every business flow forms a complete, connected loop from start to finish. Report dead code, unreachable states, disconnected modules, and incomplete flows.

## Review dimensions

1. **Entity lifecycle**: CRUD → state transitions → dependent operations → cleanup/archive.
2. **Data flow**: Source → transformation → storage → consumption. Check every pipeline step.
3. **Trigger → Action → Feedback**: For every automated process, verify there is a feedback mechanism (notification, status update, UI refresh).
4. **Frontend-Backend coverage**: Every backend API endpoint should have a corresponding frontend consumer; every frontend page should have functional backend support.
5. **Scheduler/Cron health**: Jobs register correctly, fire on time, handle failures gracefully, report status.
6. **Configuration usage**: Every env var and config flag should be consumed somewhere. Check for dead config.
7. **Status transitions**: Every status enum value should be reachable. Check for dead states.
8. **Error paths**: Exception handlers should log, update status, and not leave data in inconsistent state.

## Output format

A prioritized table:

| Priority | Flow | Status | Impact | Fix Suggestion |
|----------|------|--------|--------|----------------|
| P0 (broken) | ... | ... | ... | ... |
| P1 (incomplete) | ... | ... | ... | ... |
| P2 (minor) | ... | ... | ... | ... |

Focus on critical gaps first (dead code that should be wired, missing notifications, incomplete pipelines). Skip cosmetic issues.
