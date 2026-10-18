"""Real PostgreSQL multi-connection tracker conflicts and submission evidence races."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from applications import services
from applications.models import Application, ApplicationEvent, SubmissionArtifact
from applications.rounds import round_options
from catalog.models import ScholarshipVersion
from django.db import connections
from django.utils import timezone
from documents import services as documents
from identity.models import IdentitySession
from identity.security import IdentityError, digest
from test_applications import catalog as catalog
from test_documents import document_settings as document_settings
from test_documents import signed_client

pytestmark = pytest.mark.django_db(transaction=True)


def race(*actions):
    barrier = Barrier(len(actions))

    def run(action):
        try:
            barrier.wait(timeout=10)
            return action()
        except IdentityError as error:
            return error.code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(run, actions))


def context(catalog):
    client, user = signed_client()
    proof = IdentitySession.objects.get(digest=digest(client.session.session_key))
    version = ScholarshipVersion.objects.get(pk=catalog[2]["published_version_id"])
    key = round_options(version.rounds)[0]["round_key"]
    return user, proof, version, key


def report(target, confirmation=False):
    return {
        "to_state": target,
        "observed_at": timezone.now(),
        "evidence": "Student observed the portal; synthetic race fixture.",
        "confirm_external_submission": confirmation,
    }


def test_two_creations_for_same_round_serialize_on_owner(catalog):
    user, proof, version, key = context(catalog)
    outcomes = race(
        lambda: str(services.create_application(user, proof, version.scholarship_id, key).pk),
        lambda: str(services.create_application(user, proof, version.scholarship_id, key).pk),
    )
    assert outcomes.count("APPLICATION_ROUND_EXISTS") == 1
    assert Application.objects.filter(owner=user).count() == 1
    assert ApplicationEvent.objects.filter(actor=user).count() == 1


def test_notes_and_withdrawal_using_same_revision_have_one_winner(catalog):
    user, proof, version, key = context(catalog)
    app = services.create_application(user, proof, version.scholarship_id, key)
    outcomes = race(
        lambda: services.edit_notes(user, proof, app.pk, "Private concurrent note.", 1).revision,
        lambda: services.transition(user, proof, app.pk, report("WITHDRAWN"), 1).revision,
    )
    assert outcomes.count(2) == 1 and outcomes.count("STALE_REVISION") == 1
    app.refresh_from_db()
    assert app.revision == 2
    assert list(app.events.order_by("sequence").values_list("sequence", flat=True)) == [1, 2]


def test_submission_racing_master_edit_always_freezes_selected_old_version(catalog):
    user, proof, version, key = context(catalog)
    app = services.create_application(user, proof, version.scholarship_id, key)
    doc = documents.create_document(
        user,
        proof,
        {
            "kind": "CV",
            "title": "Original saved CV",
            "language": "en",
            "content": "Original selected content.",
        },
    )
    original = doc.current
    documents.approve_version(user, proof, doc.pk, original.pk, original.content_hash, True)
    for slot in services.requirements_data(app):
        app = services.select_artifact(
            user,
            proof,
            app.pk,
            slot["key"],
            {"version_id": original.pk, "content_hash": original.content_hash},
            app.revision,
        )
    app = services.transition(user, proof, app.pk, report("READY"), app.revision)
    expected = app.revision
    outcomes = race(
        lambda: services.transition(user, proof, app.pk, report("SUBMITTED", True), expected).state,
        lambda: (
            documents.save_version(
                user,
                proof,
                doc.pk,
                {
                    "title": "Concurrent new master",
                    "language": "en",
                    "content": "Different current content.",
                },
                1,
            ).revision
        ),
    )
    assert "SUBMITTED" in outcomes and 2 in outcomes
    assert SubmissionArtifact.objects.filter(application=app).count() == 2
    assert all(
        row.version_id == original.pk and row.content_hash == original.content_hash
        for row in SubmissionArtifact.objects.filter(application=app)
    )
    doc.refresh_from_db()
    assert doc.current_id != original.pk
