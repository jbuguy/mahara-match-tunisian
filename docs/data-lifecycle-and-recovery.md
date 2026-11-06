# Candidate data lifecycle and recovery

## Candidate export

An authenticated candidate can download `GET /api/v1/me/export`. It returns a
ZIP containing `data.json`, the candidate photo (if present), and candidate
documents stored in private object storage. The JSON includes account/profile
fields, applications, matching and roadmap data, onboarding/interview history,
and document metadata. Credentials, password hashes, and authentication tokens
are excluded. The response is marked `private, no-store`; candidates should
download the export before requesting account deletion.

## Account deletion and retention

An authenticated candidate can request deletion with `DELETE /api/v1/me`.
The API immediately disables the account, invalidates linked login identities,
removes direct identifiers and private uploaded files, clears free-text fields
that may identify the candidate, and removes onboarding/interview content.
Private object-storage deletion removes every stored object version and delete
marker for each candidate document, not just its current visible version.
An anonymized candidate record and associated hiring/profile records are held
for up to **30 days** and then purged by the hourly retention task. The worker
logs failures and retries on a later pass. Account authentication rejects
inactive users, including through the employee API.

The current implementation uses a 30-day anonymized purge window for all
remaining candidate-linked records; it does not yet support record-specific
legal holds or selectively retain a legal-record subset. Confirm that boundary
with counsel before enabling deletion in production. Deleting the account does
not retract email already delivered to an external recipient.

## Backup and restore objectives

The approved service targets are **RPO 24 hours** and **RTO 8 hours**. These
are operational objectives, not settings that the application can enforce.
The deployment owner must configure encrypted daily PostgreSQL backups and
private-object-storage backups/versioning, monitor their completion, and set a
retention period that honors the 30-day candidate purge policy. Backup copies
can retain deleted data until they expire; restoring a backup must therefore
replay candidate deletions that became due after the backup timestamp before
serving traffic.
The API's private-storage role also needs permission to list object versions
and delete object versions; otherwise deletion requests involving uploaded
documents fail closed.

### PostgreSQL backup and isolated restore check

Run these commands from a secured operations environment with PostgreSQL
client tools installed. Supply connection strings through the deployment
secret manager; do not put credentials in command history or this repository.

```powershell
pg_dump --format=custom --no-owner --file=mahara-match.dump "$env:DATABASE_URL"
pg_restore --exit-on-error --no-owner --dbname="$env:RESTORE_DATABASE_URL" mahara-match.dump
```

Restore into an isolated database, apply the current migrations, verify the
schema and representative candidate records, verify private-file access, and
record the elapsed restore time. Do not point a restore check at production or
serve traffic from it. Repeat at least quarterly and after material database
or storage changes. No production backup schedule or restore has been verified
from this repository; deployment evidence is still required to close P2.3.

## Deployment

Apply migrations before starting the API:

```powershell
python -m app.migrate
```

The lifecycle migration is `20261102000000_candidate_data_lifecycle.sql`.
Saved roadmaps also require `20261105010000_roadmap_step_required_level.sql`
to persist each step's target proficiency level.
The account-purge loop starts with each API process. To avoid duplicate work,
database row locks prevent concurrent workers from purging the same account.
The hosting operator should still monitor the `Could not purge expired
candidate account` and `Candidate data retention cleanup failed` log messages.
