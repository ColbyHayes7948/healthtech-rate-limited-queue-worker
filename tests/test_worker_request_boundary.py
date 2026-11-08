from unittest.mock import patch

from appointment_notifications import AppointmentReminderJob
from queue_worker import seed_demo_jobs, stable_job_key


def test_seed_demo_jobs_uses_batch_publish_with_stable_keys() -> None:
    captured = {}

    def fake_publish_batch(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "data": {"accepted": 2}, "error": None, "metadata": {}}

    with patch("infrai.queue.publish_batch", side_effect=fake_publish_batch):
        seed_demo_jobs()

    assert captured["queue"] == "appointment-jobs"
    assert len(captured["messages"]) == 2

    first = captured["messages"][0]
    job = AppointmentReminderJob(
        job_id="apt-1001-reminder",
        patient_id="pat-1001",
        appointment_id="apt-1001",
        patient_name="Jordan Lee",
        channel="sms",
        scheduled_for="2026-11-12T09:00:00Z",
        patient_confirmed=False,
        last_contact_hours_ago=30,
        clinic_timezone="America/New_York",
    )

    assert first["publish_id"] == stable_job_key(job)
