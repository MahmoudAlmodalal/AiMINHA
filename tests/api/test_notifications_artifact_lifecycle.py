"""Real local upload deletion invalidates selected evidence and emits one missing notice.

Scanner responses are synthetic unit fixtures reused from the application suite;
this test exercises actual storage/lifecycle/database transitions, not scanner efficacy.
"""

import pytest
from applications import services as tracker
from notifications import services
from notifications.models import Notification
from private_files import services as files
from test_application_integration import application, scholarship, select, student, upload
from test_application_integration import phase12_settings as phase12_settings

pytestmark = pytest.mark.django_db(transaction=True)


def test_deleted_selected_upload_creates_exact_current_missing_document_notice_once():
    user, proof = student()
    value = application(user, proof, scholarship())
    asset = upload(user)
    value = select(user, proof, value, asset=asset)
    services.schedule_owner(user.pk)
    assert not Notification.objects.filter(owner=user, category="DOCUMENT_MISSING").exists()
    files.delete_owned(user.pk, asset.pk)
    asset.refresh_from_db()
    assert asset.state != "ACCEPTED"
    assert tracker.requirements_data(value)[0]["status"] == "MISSING"
    services.schedule_owner(user.pk)
    services.schedule_owner(user.pk)
    notification = Notification.objects.get(owner=user, category="DOCUMENT_MISSING")
    assert notification.application_id == value.pk
    assert notification.event_id == value.requirements.get().pk
