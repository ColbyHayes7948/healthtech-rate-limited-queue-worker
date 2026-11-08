from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


NotificationAction = Literal["send_sms_reminder", "skip_recent_contact", "manual_review"]


class AppointmentReminderJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    patient_id: str = Field(min_length=1)
    appointment_id: str = Field(min_length=1)
    patient_name: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    scheduled_for: str = Field(min_length=1)
    patient_confirmed: bool
    last_contact_hours_ago: int = Field(ge=0)
    clinic_timezone: str = Field(min_length=1)


class NotificationDecision(BaseModel):
    action: NotificationAction
    reason: str
    message: str


RECENT_CONTACT_WINDOW_HOURS = 24


def decide_notification(job: AppointmentReminderJob) -> NotificationDecision:
    if job.channel != "sms":
        return NotificationDecision(
            action="manual_review",
            reason="unsupported_channel",
            message=f"Route appointment {job.appointment_id} to staff review.",
        )

    if job.last_contact_hours_ago < RECENT_CONTACT_WINDOW_HOURS:
        return NotificationDecision(
            action="skip_recent_contact",
            reason="recent_contact",
            message=f"Skip reminder for {job.patient_name}; contacted {job.last_contact_hours_ago}h ago.",
        )

    return NotificationDecision(
        action="send_sms_reminder",
        reason="eligible_sms_reminder",
        message=f"Send SMS reminder for appointment {job.appointment_id}.",
    )
