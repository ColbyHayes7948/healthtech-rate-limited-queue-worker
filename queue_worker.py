import hashlib
import json
import sys
import time
from typing import Iterable, List

import infrai
from appointment_notifications import AppointmentReminderJob, decide_notification

SOURCE_QUEUE = "appointment-jobs"
DLQ_QUEUE = "appointment-jobs-dlq"
MAX_MESSAGES = 2
VISIBILITY_TIMEOUT = 60
PER_MESSAGE_DELAY_SECONDS = 0.5


def stable_job_key(job: AppointmentReminderJob) -> str:
    digest = hashlib.sha256(f"{job.appointment_id}:{job.patient_id}:{job.scheduled_for}".encode("utf-8")).hexdigest()
    return digest[:16]


def bootstrap_queues() -> None:
    infrai.queue.create(name=DLQ_QUEUE)
    infrai.queue.create(name=SOURCE_QUEUE, dead_letter_queue=DLQ_QUEUE, max_retries=3)
    source_state = infrai.queue.get(SOURCE_QUEUE)
    print(json.dumps(source_state["data"], indent=2))


def demo_jobs() -> List[AppointmentReminderJob]:
    return [
        AppointmentReminderJob(
            job_id="apt-1001-reminder",
            patient_id="pat-1001",
            appointment_id="apt-1001",
            patient_name="Jordan Lee",
            channel="sms",
            scheduled_for="2026-11-12T09:00:00Z",
            patient_confirmed=False,
            last_contact_hours_ago=30,
            clinic_timezone="America/New_York",
        ),
        AppointmentReminderJob(
            job_id="apt-1002-reminder",
            patient_id="pat-1002",
            appointment_id="apt-1002",
            patient_name="Alex Gomez",
            channel="sms",
            scheduled_for="2026-11-12T10:00:00Z",
            patient_confirmed=False,
            last_contact_hours_ago=6,
            clinic_timezone="America/Chicago",
        ),
    ]


def seed_demo_jobs() -> None:
    jobs = demo_jobs()
    messages = []
    for job in jobs:
        payload = job.model_dump()
        payload["publish_id"] = stable_job_key(job)
        messages.append(payload)

    result = infrai.queue.publish_batch(queue=SOURCE_QUEUE, messages=messages)
    print(json.dumps(result["data"], indent=2))


def _extract_messages(data: dict) -> List[dict]:
    if isinstance(data, dict):
        items = data.get("messages")
        if isinstance(items, list):
            return items
        single = data.get("message")
        if isinstance(single, dict):
            return [single]
    return []


def process_once() -> List[str]:
    consumed = infrai.queue.consume(
        queue=SOURCE_QUEUE,
        max_messages=MAX_MESSAGES,
        visibility_timeout=VISIBILITY_TIMEOUT,
    )
    messages = _extract_messages(consumed["data"])
    outputs: List[str] = []

    for message in messages:
        body = message.get("payload") or {}
        job = AppointmentReminderJob.model_validate(body)
        decision = decide_notification(job)
        output = f"{job.job_id} -> {decision.action}"
        print(output)
        outputs.append(output)
        infrai.queue.ack(queue=SOURCE_QUEUE, message_id=message["message_id"])
        time.sleep(PER_MESSAGE_DELAY_SECONDS)

    return outputs


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 2:
        print("usage: python queue_worker.py [bootstrap|seed-demo|run-once]")
        return 1

    command = args[1]
    if command == "bootstrap":
        bootstrap_queues()
        return 0
    if command == "seed-demo":
        seed_demo_jobs()
        return 0
    if command == "run-once":
        process_once()
        return 0

    print(f"unknown command: {command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
