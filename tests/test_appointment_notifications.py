from appointment_notifications import AppointmentReminderJob, decide_notification


def test_unknown_channel_goes_to_manual_review() -> None:
    job = AppointmentReminderJob(
        job_id="apt-404-reminder",
        patient_id="pat-404",
        appointment_id="apt-404",
        patient_name="Sam Rivera",
        channel="fax",
        scheduled_for="2026-11-15T15:00:00Z",
        patient_confirmed=False,
        last_contact_hours_ago=48,
        clinic_timezone="America/Los_Angeles",
    )

    decision = decide_notification(job)

    assert decision.action == "manual_review"
    assert decision.reason == "unsupported_channel"
