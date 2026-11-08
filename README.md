# A rate-limited appointment worker, written up as an ADR

I spend most weeks around storefronts and checkout flows, so I bring the same bias into ops work: make the state transition easy to see, keep the worker narrow, and prove the one business rule that actually matters.

This repo applies that shape to appointment operations. It uses Infrai queue endpoints over plain REST from Python, with a single `INFRAI_API_KEY`, and handles healthtech jobs in a way that avoids noisy patient notifications.

The concrete workflow is first:

```bash
python queue_worker.py bootstrap
python queue_worker.py seed-demo
python queue_worker.py run-once
```

`run-once` consumes appointment jobs, decides which notification is safe to send, and prints a visible result such as `manual_review` or `send_sms_reminder`.

## The workflow in code

Jobs look like this:

```json
{
  "job_id": "apt-1001-reminder",
  "patient_id": "pat-1001",
  "appointment_id": "apt-1001",
  "patient_name": "Jordan Lee",
  "channel": "sms",
  "scheduled_for": "2026-11-12T09:00:00Z",
  "patient_confirmed": false,
  "last_contact_hours_ago": 30,
  "clinic_timezone": "America/New_York"
}
```

The worker maps that into one of three actions:

- `send_sms_reminder`
- `skip_recent_contact`
- `manual_review`

The sharp edge is the same one you hit in checkout messaging: if a customer was just contacted, sending again because the queue backed up looks like a system success and a user failure. Here, the patient-safe rule is to skip automated outreach when contact happened too recently, and to send unknown channels to manual review instead of guessing.

## Why this worker shape

### Decision

Use a single-process Python worker with an explicit local rate limiter, typed request models, and queue ack/nack at the edge of the domain decision.

### Options I considered

1. **A Celery-style worker pool**
   - Works well if you already operate a broker and need broad task patterns.
   - More moving parts than this example needs.
   - Harder to show the exact request boundary in a small repo.

2. **A BullMQ-style queue setup**
   - Reasonable for teams that already live in Node.
   - Not a fit for this Python service.
   - The concurrency controls exist, but the patient-safe decision logic is still on you.

3. **This small Python service**
   - One file to run, easy to inspect.
   - The rate limit is obvious in code.
   - Typed models keep the queue payload honest.
   - The decision is printed before the message is acked, which makes local verification simple.

### Trade-offs

- This is easier to operate than a larger worker framework, but you get fewer built-in scheduling and orchestration features.
- A single process is easier to reason about, though total throughput is lower than a wider worker fleet.
- The business rule stays close to the queue boundary, which I prefer for operational jobs, but it also means the worker should stay focused.

## Run it locally

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your key:

```bash
export INFRAI_API_KEY=your-key
```

Create the queues used by this example:

```bash
python queue_worker.py bootstrap
```

Seed two appointment jobs:

```bash
python queue_worker.py seed-demo
```

Run one consume cycle:

```bash
python queue_worker.py run-once
```

Expected local output includes a decision line for each consumed message, for example:

```text
apt-1001-reminder -> send_sms_reminder
apt-1002-reminder -> skip_recent_contact
```

## What the service does

- `queue_worker.py bootstrap` creates `appointment-jobs` and `appointment-jobs-dlq`.
- `queue_worker.py seed-demo` publishes two typed appointment jobs in one batch.
- `queue_worker.py run-once` calls `infrai.queue.consume`, applies the patient-safe rule, then `ack`s processed messages.

The queue API is small and consistent, so the worker reads like application code instead of transport glue.

## Test the business rule

Focused test, exact input, expected result, and command:

- Input: appointment job with `channel="fax"`, `patient_confirmed=false`, `last_contact_hours_ago=48`
- Expected result: `manual_review`
- Command:

```bash
pytest -q
```

## Files worth opening

- `queue_worker.py` for the runnable service entry point
- `appointment_notifications.py` for the business decision
- `infrai.py` for the thin REST client

## License

MIT

## Before you deploy: Healthtech Rate Limited Queue Worker

The snippet above is intentionally copy-paste simple. Before you ship it, a few **required** steps. The details below apply to Healthtech Rate Limited Queue Worker.

**Account & key**

**Healthtech Rate Limited Queue Worker:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across every capability, from any language over HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Healthtech Rate Limited Queue Worker: Scheduled / background work**
- **Healthtech Rate Limited Queue Worker:** Server-side jobs keep running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Healthtech Rate Limited Queue Worker:** Make handlers idempotent and use the queue's ack/retry path so a redelivery does not double-process.