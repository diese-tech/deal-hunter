# AI Workflow Guardrails

Review this document before implementation, debugging, refactoring, migrations, or production fixes in this repository.

## Core Rule

Move fast, but move surgically. Prefer the smallest safe change that solves the measured problem. Avoid broad rewrites, speculative refactors, or unrelated cleanup.

## Repo-Specific Focus

- Respect retailer and third-party rate limits.
- Make ingestion retry-safe and deduplicated.
- Prefer queue-based scraping workflows over burst fan-out.
- Cache and batch work where it reduces external pressure.
- Degrade gracefully when external services fail or return partial data.
- Keep crawler/parser changes low-blast-radius and easy to roll back.

## Required Before Changing Code

- Identify the specific problem and files likely involved.
- Name the expected impact and rollback path.
- Check whether the change affects scheduled jobs, third-party APIs, Discord delivery, data integrity, or production operations.
- Avoid touching unrelated files.

## Architecture Defaults

- Prefer queue-based async processing over synchronous fan-out.
- Prefer append-only raw observations before derived deal notifications.
- Prefer indexed dedupe keys over repeated broad scans.
- Prefer bounded concurrency, batching, and backoff.
- Prefer idempotent and retry-safe jobs.

## Change Review Checklist

Before finalizing a change, answer what changed, why it is safe, what could break, how to roll back, and what validation proves the change.
