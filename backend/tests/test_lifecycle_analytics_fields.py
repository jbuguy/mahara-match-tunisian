from app.models import (
    CandidateProfile,
    CourseEnrollmentStatus,
    JobApplicationStatusEvent,
    application_age_group,
)


def test_application_status_event_has_backfill_marker():
    event = JobApplicationStatusEvent(
        application_id="application-1",
        to_status="submitted",
        changed_by="system",
        backfilled=True,
    )
    assert event.backfilled is True
    assert event.changed_by == "system"


def test_candidate_profile_birth_year_is_optional():
    profile = CandidateProfile(user_id="candidate-1", skills=[], birth_year=None)
    assert profile.birth_year is None


def test_age_group_is_derived_in_analytics_layer():
    assert application_age_group(2002, 2026) == "15-24"
    assert application_age_group(1995, 2026) == "25-34"
    assert application_age_group(1980, 2026) == "35+"
    assert application_age_group(None, 2026) is None
