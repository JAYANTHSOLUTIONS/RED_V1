# API CHANGE POLICY

As of Phase 18, the RED_V1 backend API is **FROZEN**. This means the frontend team is relying on the exact structure, naming, and behavior documented in the `openapi.json` and associated API guides.

To maintain stability and prevent integration failures, all future backend modifications must adhere to the following policy.

## 1. Allowed Without Contract Break (Non-Breaking)
These changes can be deployed directly as they do not affect frontend clients.
- Internal implementation changes and refactoring.
- Database query optimizations and index additions.
- Logging and observability improvements.
- Security patches that do not alter request/response shapes.
- Bug fixes that restore the system to its *documented* API behavior.

## 2. Requires API Review (Additive Changes)
These changes are generally safe but require review to ensure naming consistency and documentation updates.
- Adding a brand new endpoint.
- Adding a new, optional field to a Request payload.
- Adding a new field to a Response payload.
- Expanding an enum with a new value (must coordinate with frontend if the frontend has strict enum handling).

## 3. Breaking Changes (Strictly Forbidden Post-Freeze)
These changes **will break** the frontend and are forbidden without a formal version bump (e.g., to `/api/v2`) or explicit, coordinated deprecation windows.
- Renaming an existing endpoint path.
- Changing an endpoint's HTTP method.
- Renaming an existing field in a Request or Response payload.
- Removing an existing field from a Response payload.
- Changing a previously optional Request field to required.
- Changing the data type of a field (e.g., from `int` to `string`).
- Removing or renaming an existing enum value.
- Changing the HTTP status code returned for a specific outcome.
- Altering the authentication/authorization requirements for an existing endpoint.

If a breaking change is absolutely unavoidable due to a critical security flaw or fundamental domain shift, it must go through an explicit API Review process involving both the backend and frontend leads.
