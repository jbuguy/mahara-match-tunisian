# Development Guidelines

These guidelines are here to keep changes local, understandable, and safe to extend. A feature should usually be changeable by editing its own module and a small number of tests—not by touching hundreds of files.

## Start with the owner and boundary

Before coding, identify the feature that owns the behavior and the public contract other code uses. Keep implementation details inside that feature. Use the repository layout as a starting point:

- Backend feature behavior belongs in `back/app/features/<feature>/`.
- Shared backend infrastructure and genuinely reusable code belong in `back/app/shared/` or the shared packages under `back/`.
- Frontend feature pages and UI belong under `front/src/`; shared API, types, and UI utilities belong in their existing shared locations.
- Database changes belong in ordered files under `migrations/`.

If the right owner is unclear, trace the current request or user interaction from its entry point to the implementation before adding another layer.

## Keep responsibilities cohesive

Each module should have one clear reason to change. A typical backend request should follow a direct path:

1. **Route/handler:** HTTP concerns, input validation, status codes, and response shape.
2. **Feature service:** business rules and coordination for that feature.
3. **Repository/data layer:** persistence queries and mapping to domain data.

On the frontend, keep page composition, reusable UI, state/interaction logic, and HTTP calls in their appropriate existing modules. Avoid putting business rules in route handlers or large page components. Avoid creating abstractions that only forward a call to another module.

## Keep coupling low

- Features may use another feature's documented public interface, but should not import its private files or reach into its database tables directly.
- Prefer dependencies that point toward stable contracts and shared infrastructure. Avoid circular imports and feature-to-feature chains.
- Keep API schemas and shared types explicit. Update their callers when a contract changes; do not hide incompatibilities behind adapters that only pass data through.
- Centralize authentication, database access, configuration, logging, and error handling. Do not create a second app, server, client, or configuration system for one feature.
- Add something to shared code only when there is a real shared use and a clear common behavior. Similar-looking code with different rules may belong in separate feature modules.

## Make behavior easy to test

- Put business rules in functions or services that can be called without starting a web server or rendering the whole application.
- Pass external dependencies (database sessions, provider clients, clocks, and other services) through established dependency injection points rather than hiding them in globals.
- Test the behavior at the smallest useful boundary: unit tests for rules, route tests for HTTP contracts, and frontend tests for user-visible interactions.
- Test important failure cases and authorization boundaries, not only the happy path.
- Keep tests independent of real credentials and external services; use the repository's mocks or test doubles.

## Make code readable

- Prefer specific names and short functions that make the normal flow obvious.
- Keep modules focused. Split a file when it has unrelated responsibilities or becomes hard to navigate, not just to meet a line-count target.
- Make data transformations and error handling explicit. Comments should explain a non-obvious reason or constraint, not restate the code.
- Follow the conventions already used by the surrounding feature. Avoid introducing a second style or framework for the same job.

## Add a feature with a small, reviewable change

1. Trace the existing behavior and find its owning frontend and backend feature modules.
2. Define the user-visible behavior and any API or data contract change before implementation.
3. Implement the vertical slice in the existing application: frontend interaction, unified API call, feature route/service, and persistence only if needed.
4. Reuse shared authentication, authorization, database, configuration, and error handling.
5. Add or update focused tests for the behavior and its contract.
6. Review the complete change for accidental duplication, private cross-feature imports, and unrelated edits.

For database changes, add an ordered migration and update the code that reads or writes the affected data. Consider existing data and deployment order; do not rely on a developer's local database state.

## Keep the change radius visible

Before finishing, inspect `git diff --stat` and `git diff --name-only`. A feature should normally touch its implementation, contract if needed, and focused tests. A change spanning many unrelated modules is a signal to pause and check whether:

- the behavior has a clear owner;
- callers are using a stable public interface;
- duplicated implementations or global configuration are causing unnecessary edits;
- a mechanical rename or generated-file change can be separated from the behavior change.

There is no fixed file-count limit: migrations and deliberate API changes can be broad. But a change approaching dozens of files needs a clear explanation, and hundreds of files should trigger an investigation before review. Keep mechanical changes in a separate, reviewable commit when practical.

## Before opening a change

- Run the relevant checks documented in the root `README.md` and the checks for the modules you changed.
- Confirm the frontend uses the unified router and the backend registers endpoints in the unified application.
- Search for stale imports, aliases, scripts, or runtime references introduced by the change.
- Summarize what behavior changed, the tests run, and any known gap.

The design goal is not the fewest files at any cost. It is a clear owner, a small dependency surface, and changes whose impact is easy to predict.
