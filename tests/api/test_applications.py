"""Phase12 owned student reports, immutable evidence and closed official integration."""

import uuid
from datetime import timedelta

import pytest
from applications import services
from applications.models import (
    Application,
    ApplicationEvent,
    ApplicationRequirement,
    OfficialStatusReport,
    SelectedArtifact,
    SubmissionArtifact,
)
from applications.rounds import round_options
from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from documents.models import SubmissionSnapshot
from identity.models import IdentitySession
from identity.security import IdentityError, digest
from privacy.models import PrivacyAudit
from test_catalog import create_source, publish
from test_catalog import signed_client as admin_client
from test_documents import create as create_document
from test_documents import document_settings as document_settings
from test_documents import mutate, signed_client

pytestmark = pytest.mark.django_db


def request(client, method, path, data=None, *, revision=None, key=None):
    token = client.get("/api/v1/session/csrf").json()["csrf_token"]
    headers = {"HTTP_X_CSRFTOKEN": token, "HTTP_IDEMPOTENCY_KEY": key or str(uuid.uuid4())}
    if revision is not None:
        headers["HTTP_IF_MATCH"] = f'"{revision}"'
    return getattr(client, method)("/api/v1/" + path, data=data, format="json", **headers)


@pytest.fixture
def catalog():
    client, _ = admin_client()
    source = create_source(client)
    value = publish(
        client,
        source,
        required_documents=["Synthetic transcript", "Synthetic CV"],
        rounds=[{"kind": "UNKNOWN", "label": "Reviewed 2027 round"}],
    )
    return client, source, value


def create_application(client, value, *, index=0, key=None):
    options = client.get("/api/v1/applications/round-options", {"scholarship_id": value["id"]})
    assert options.status_code == 200, options.content
    response = request(
        client,
        "post",
        "applications",
        {"scholarship_id": value["id"], "round_key": options.json()["items"][index]["round_key"]},
        key=key,
    )
    assert response.status_code == 201, response.content
    return response.json()


def approved_document(client):
    doc = create_document(client)
    response = mutate(
        client,
        f"documents/{doc['id']}/approvals",
        {
            "version_id": doc["current"]["id"],
            "content_hash": doc["current"]["content_hash"],
            "confirm": True,
        },
    )
    assert response.status_code == 200, response.content
    return doc


def attach(client, app, doc, slot=0):
    response = request(
        client,
        "put",
        f"applications/{app['id']}/requirements/{app['requirements'][slot]['key']}/artifact",
        {"version_id": doc["current"]["id"], "content_hash": doc["current"]["content_hash"]},
        revision=app["revision"],
    )
    assert response.status_code == 200, response.content
    return response.json()


def move(client, app, target, *, confirm=False, key=None):
    return request(
        client,
        "post",
        f"applications/{app['id']}/transitions",
        {
            "to_state": target,
            "observed_at": (timezone.now() - timedelta(seconds=1)).isoformat(),
            "evidence": "Student read the external portal; this is a student report.",
            "confirm_external_submission": confirm,
        },
        revision=app["revision"],
        key=key,
    )


def ready(client, value):
    app = create_application(client, value)
    doc = approved_document(client)
    for slot in range(len(app["requirements"])):
        app = attach(client, app, doc, slot)
    response = move(client, app, "READY")
    assert response.status_code == 200, response.content
    return response.json(), doc


def test_create_pins_exact_reviewed_requirements_unknown_profile_and_round(catalog):
    client, user = signed_client()
    app = create_application(client, catalog[2])
    assert app["state"] == "PREPARING" and app["revision"] == 1
    assert app["profile_version_id"] is None
    assert app["requirements_known"] and app["missing_count"] == 2
    assert [row["label"] for row in app["requirements"]] == ["Synthetic transcript", "Synthetic CV"]
    assert all(
        row["kind"] == "DOCUMENT" and row["status"] == "MISSING" for row in app["requirements"]
    )
    assert not app["official_integration_available"] and app["official_reports"] == []
    assert app["deadline"]["eligible"] is False and app["deadline"]["closes_at"] is None
    stored = Application.objects.get(pk=app["id"])
    assert stored.owner == user
    history = client.get(f"/api/v1/applications/{app['id']}/history").json()["items"]
    assert len(history) == 1 and history[0]["source"] == "STUDENT_REPORTED"
    assert history[0]["scholarship_version_id"] == app["scholarship_version_id"]
    assert client.get("/api/v1/applications").json()["counts"]["PREPARING"] == 1


def test_requirements_empty_stays_unknown_and_cannot_be_ready():
    admin, _ = admin_client()
    value = publish(admin, create_source(admin), required_documents=[])
    client, _ = signed_client()
    app = create_application(client, value)
    assert not app["requirements_known"] and app["requirements"] == []
    assert move(client, app, "READY").status_code == 409


def test_explicit_external_submission_freezes_exact_evidence_and_audits_new_master(catalog):
    client, _ = signed_client()
    app, doc = ready(client, catalog[2])
    assert move(client, app, "SUBMITTED").status_code == 409
    response = move(client, app, "SUBMITTED", confirm=True)
    assert response.status_code == 200, response.content
    app = response.json()
    snapshots = client.get(f"/api/v1/applications/{app['id']}/submitted-artifacts").json()["items"]
    assert (
        len(snapshots) == 2
        and len(SubmissionSnapshot.objects.filter(application_ref=app["id"])) == 1
    )
    assert all(
        row["version_id"] == doc["current"]["id"]
        and row["content_hash"] == doc["current"]["content_hash"]
        for row in snapshots
    )
    changed = mutate(
        client,
        f"documents/{doc['id']}/versions",
        {
            "title": "Different master title",
            "language": "en",
            "content": "New manually edited master.",
        },
        revision=1,
    )
    assert changed.status_code == 200
    assert changed.json()["current"]["id"] != snapshots[0]["version_id"]
    assert (
        client.get(f"/api/v1/applications/{app['id']}/submitted-artifacts").json()["items"]
        == snapshots
    )
    assert (
        request(
            client,
            "put",
            f"applications/{app['id']}/requirements/{app['requirements'][0]['key']}/artifact",
            {"clear": True},
            revision=app["revision"],
        ).status_code
        == 409
    )
    assert move(client, app, "PREPARING").status_code == 409


@pytest.mark.parametrize(
    "target", ["SUBMITTED", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "PREPARING"]
)
def test_preparing_rejects_skipped_or_same_status_edges(catalog, target):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    assert move(client, app, target, confirm=target == "SUBMITTED").status_code == 409
    assert ApplicationEvent.objects.filter(application_id=app["id"]).count() == 1


@pytest.mark.parametrize("outcome", ["ACCEPTED", "REJECTED", "WITHDRAWN"])
def test_direct_student_outcomes_are_allowed_and_terminals_never_reverse(catalog, outcome):
    client, _ = signed_client()
    app, _ = ready(client, catalog[2])
    response = move(client, app, "SUBMITTED", confirm=True)
    assert response.status_code == 200, response.content
    response = move(client, response.json(), outcome)
    assert response.status_code == 200, response.content
    app = response.json()
    assert app["allowed_transitions"] == []
    assert move(client, app, "PREPARING").status_code == 409
    assert move(client, app, "SUBMITTED", confirm=True).status_code == 409
    correction = request(
        client,
        "post",
        f"applications/{app['id']}/corrections",
        {
            "correction_of_sequence": 1,
            "observed_at": timezone.now().isoformat(),
            "evidence": "Additional student evidence, without changing the reported outcome.",
            "reason": "Correct an earlier evidence description.",
        },
        revision=app["revision"],
    )
    assert correction.status_code == 200, correction.content
    assert correction.json()["state"] == outcome
    history = client.get(f"/api/v1/applications/{app['id']}/history").json()["items"]
    assert history[-1]["kind"] == "CORRECTION" and history[-1]["correction_of_sequence"] == 1
    assert [row["sequence"] for row in history] == list(range(1, len(history) + 1))


def test_under_review_path_ready_backedge_and_notes_keep_manifest(catalog):
    client, _ = signed_client()
    app, _ = ready(client, catalog[2])
    back = move(client, app, "PREPARING")
    assert back.status_code == 200, back.content
    app = move(client, back.json(), "READY").json()
    app = move(client, app, "SUBMITTED", confirm=True).json()
    app = move(client, app, "UNDER_REVIEW").json()
    before = client.get(f"/api/v1/applications/{app['id']}/submitted-artifacts").json()
    note = request(
        client,
        "put",
        f"applications/{app['id']}/notes",
        {"notes": "<private>Owner notes</private>"},
        revision=app["revision"],
    )
    assert note.status_code == 200, note.content
    assert (
        note.json()["state"] == "UNDER_REVIEW"
        and note.json()["notes"] == "<private>Owner notes</private>"
    )
    assert client.get(f"/api/v1/applications/{app['id']}/submitted-artifacts").json() == before
    assert move(client, note.json(), "ACCEPTED").status_code == 200


@pytest.mark.parametrize(
    "route",
    [
        "",
        "/history",
        "/requirements",
        "/artifact-options",
        "/submitted-artifacts",
        "/artifact-deletion-requests",
    ],
)
def test_cross_student_and_admin_reads_deny_audit_without_private_data(catalog, route):
    owner, _ = signed_client()
    app = create_application(owner, catalog[2])
    for client in (signed_client()[0], catalog[0]):
        response = client.get(f"/api/v1/applications/{app['id']}" + route)
        assert response.status_code == 403, response.content
        assert app["title"] not in response.content.decode()
        assert response["Cache-Control"] == "no-store"
    assert PrivacyAudit.objects.filter(resource_id=app["id"], outcome="DENY").count() >= 2


def test_attach_unapproved_foreign_hash_spoof_or_xor_is_denied(catalog):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    doc = create_document(client)
    foreign_client, _ = signed_client()
    foreign = approved_document(foreign_client)
    path = f"applications/{app['id']}/requirements/{app['requirements'][0]['key']}/artifact"
    for data, code in [
        ({"version_id": doc["current"]["id"], "content_hash": doc["current"]["content_hash"]}, 409),
        (
            {
                "version_id": foreign["current"]["id"],
                "content_hash": foreign["current"]["content_hash"],
            },
            403,
        ),
        ({"version_id": doc["current"]["id"], "content_hash": "0" * 64}, 409),
        (
            {
                "version_id": doc["current"]["id"],
                "asset_id": str(uuid.uuid4()),
                "content_hash": "0" * 64,
            },
            400,
        ),
        ({"content_hash": "0" * 64}, 400),
    ]:
        response = request(client, "put", path, data, revision=app["revision"])
        assert response.status_code == code, response.content
    assert not SelectedArtifact.objects.filter(requirement__application_id=app["id"]).exists()


def test_artifact_options_only_exact_approved_owned_versions(catalog):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    expected = approved_document(client)
    create_document(client)
    approved_document(signed_client()[0])
    response = client.get(f"/api/v1/applications/{app['id']}/artifact-options")
    assert response.status_code == 200, response.content
    assert [row["id"] for row in response.json()["versions"]] == [expected["current"]["id"]]
    assert response.json()["files"] == []
    assert "content" not in response.json()["versions"][0]


def test_idempotent_create_notes_stale_cas_and_csrf(catalog):
    client, _ = signed_client()
    key = str(uuid.uuid4())
    app = create_application(client, catalog[2], key=key)
    assert create_application(client, catalog[2], key=key)["id"] == app["id"]
    options = client.get(
        "/api/v1/applications/round-options", {"scholarship_id": catalog[2]["id"]}
    ).json()
    assert (
        request(
            client,
            "post",
            "applications",
            {"scholarship_id": catalog[2]["id"], "round_key": options["items"][0]["round_key"]},
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/applications/{app['id']}/notes", {"notes": "No CSRF"}, format="json"
        ).status_code
        == 403
    )
    key = str(uuid.uuid4())
    path = f"applications/{app['id']}/notes"
    response = request(client, "put", path, {"notes": "Private note."}, revision=1, key=key)
    assert response.status_code == 200, response.content
    assert (
        request(client, "put", path, {"notes": "Private note."}, revision=1, key=key).status_code
        == 200
    )
    assert ApplicationEvent.objects.filter(application_id=app["id"]).count() == 2
    assert request(client, "put", path, {"notes": "Stale"}, revision=1).status_code == 412
    assert request(client, "put", path, {"notes": "Missing revision"}).status_code == 412


@pytest.mark.parametrize(
    "extra",
    [
        {"owner_id": str(uuid.uuid4())},
        {"source": "VERIFIED_OFFICIAL"},
        {"official": True},
        {"actor": "AI"},
    ],
)
def test_client_cannot_forge_origin_or_authority(catalog, extra):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    response = request(
        client,
        "post",
        f"applications/{app['id']}/transitions",
        {
            "to_state": "WITHDRAWN",
            "observed_at": timezone.now().isoformat(),
            "evidence": "Student report",
            **extra,
        },
        revision=1,
    )
    assert response.status_code == 400, response.content
    assert Application.objects.get(pk=app["id"]).state == "PREPARING"


@pytest.mark.parametrize("observed", ["2026-01-01T12:00:00", "2099-01-01T00:00:00Z", "not-a-date"])
def test_naive_future_invalid_observation_is_not_recorded(catalog, observed):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    response = request(
        client,
        "post",
        f"applications/{app['id']}/transitions",
        {"to_state": "WITHDRAWN", "observed_at": observed, "evidence": "Student report"},
        revision=1,
    )
    assert response.status_code == 400, response.content


def test_official_stream_is_separate_live_unavailable_synthetic_never_verified(catalog, settings):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    with pytest.raises(IdentityError) as error:
        services.record_official_status(application_id=app["id"], status="ACCEPTED")
    assert error.value.status_code == 503
    settings.LOCAL = True
    proof = services.fixed_synthetic_official_proof(uuid.UUID(app["id"]))
    response = client.get(f"/api/v1/applications/{app['id']}").json()
    assert response["state"] == "PREPARING" and not response["official_integration_available"]
    assert response["official_reports"][0]["origin"] == "SYNTHETIC_LOCAL"
    assert response["official_reports"][0]["verified_official"] is False
    assert ApplicationEvent.objects.filter(application_id=app["id"]).count() == 1
    settings.LOCAL = False
    with pytest.raises(IdentityError):
        services.fixed_synthetic_official_proof(uuid.UUID(app["id"]))
    with pytest.raises(DatabaseError), transaction.atomic():
        OfficialStatusReport.objects.filter(pk=proof.pk).update(status="ACCEPTED")
    with pytest.raises(DatabaseError), transaction.atomic():
        OfficialStatusReport.objects.create(
            application_id=app["id"],
            status="ACCEPTED",
            source_url="https://fixtures.example.invalid",
            observed_at=timezone.now(),
            evidence_ref="Fake verified claim",
            origin="VERIFIED_OFFICIAL",
        )


def test_saved_relationship_revision_unsave_preserves_application(catalog):
    client, user = signed_client()
    value = catalog[2]
    saved = request(client, "post", "saved-scholarships", {"scholarship_id": value["id"]})
    assert saved.status_code == 200, saved.content
    assert services.relationship_exists(user.pk, uuid.UUID(value["id"]))
    app = create_application(client, value)
    response = request(client, "delete", f"saved-scholarships/{value['id']}", revision=1)
    assert response.status_code == 200 and not response.json()["active"]
    assert client.get("/api/v1/saved-scholarships").json()["items"] == []
    assert services.relationship_exists(user.pk, uuid.UUID(value["id"]), app["round_key"])
    assert move(client, app, "WITHDRAWN").status_code == 200
    assert not services.relationship_exists(user.pk, uuid.UUID(value["id"]))
    assert (
        request(client, "post", "saved-scholarships", {"scholarship_id": value["id"]}).json()[
            "revision"
        ]
        == 3
    )


def test_sql_history_and_snapshot_mutation_denied(catalog):
    client, user = signed_client()
    app, _ = ready(client, catalog[2])
    app = move(client, app, "SUBMITTED", confirm=True).json()
    for model, changes in [
        (ApplicationEvent, {"to_state": "ACCEPTED"}),
        (SubmissionArtifact, {"content_hash": "0" * 64}),
        (ApplicationRequirement, {"label": "Silently changed"}),
    ]:
        with pytest.raises(DatabaseError), transaction.atomic():
            model.objects.filter(application_id=app["id"]).update(**changes)
    with pytest.raises(DatabaseError), transaction.atomic():
        SelectedArtifact.objects.filter(requirement__application_id=app["id"]).delete()
    with pytest.raises(DatabaseError), transaction.atomic():
        Application.objects.filter(pk=app["id"]).update(state="PREPARING")
    with pytest.raises(DatabaseError), transaction.atomic():
        Application.objects.filter(pk=app["id"]).delete()
    proof = IdentitySession.objects.get(digest=digest(client.session.session_key))
    value = Application.objects.get(pk=app["id"])
    with pytest.raises(DatabaseError), transaction.atomic():
        ApplicationEvent.objects.create(
            application=value,
            sequence=value.revision + 1,
            actor=user,
            session_proof=proof,
            scholarship_version_id=value.scholarship_version_id,
            from_state="SUBMITTED",
            to_state="PREPARING",
            kind="TRANSITION",
            observed_at=timezone.now(),
            evidence="Try illicit rollback",
            manifest_snapshot=services.manifest(value),
        )


def test_sql_selection_without_history_cannot_commit(catalog):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    doc = approved_document(client)
    slot = ApplicationRequirement.objects.get(
        application_id=app["id"], key=app["requirements"][0]["key"]
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        SelectedArtifact.objects.create(
            requirement=slot,
            version_id=doc["current"]["id"],
            content_hash=doc["current"]["content_hash"],
        )
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_round_keys_survive_date_edits_new_distinct_labels_and_deny_ambiguity():
    a = round_options([{"kind": "UNKNOWN", "label": "  Spring 2027  "}])[0]
    b = round_options(
        [{"kind": "CONFIRMED", "label": "spring 2027", "closes_at": "2027-01-01T00:00:00Z"}]
    )[0]
    assert a["round_key"] == b["round_key"]
    assert (
        a["round_key"]
        != round_options([{"kind": "UNKNOWN", "label": "Spring 2028"}])[0]["round_key"]
    )
    assert round_options([])[0]["kind"] == "UNKNOWN"
    assert (
        round_options([])[0]["round_key"]
        == round_options([{"kind": "UNKNOWN", "label": ""}])[0]["round_key"]
    )
    for rows in [
        [{"label": "A"}, {"label": " a "}],
        [{"label": ""}, {"label": "B"}],
        [{"label": ""}, {"label": ""}],
    ]:
        with pytest.raises(IdentityError) as error:
            round_options(rows)
        assert error.value.status_code == 503


def test_rebase_is_explicit_clears_drafts_and_preserves_pinned_history(catalog):
    client, _ = signed_client()
    app = create_application(client, catalog[2])
    doc = approved_document(client)
    app = attach(client, app, doc)
    before = client.get(f"/api/v1/applications/{app['id']}/history").json()["items"]
    moderator, source, prior = catalog
    from test_catalog import candidate_payload, moderate, post

    response = post(
        moderator,
        f"admin/scholarships/{prior['id']}/versions",
        candidate_payload(
            source,
            required_documents=["New reviewed document"],
            rounds=[{"kind": "UNKNOWN", "label": "Reviewed 2027 round"}],
        ),
        revision=prior["revision"],
    )
    assert response.status_code == 200, response.content
    reviewed = moderate(moderator, response.json())
    assert reviewed.status_code == 200, reviewed.content
    stale = client.get(f"/api/v1/applications/{app['id']}").json()
    assert stale["source_changed"] and stale["can_rebase"]
    assert move(client, stale, "READY").status_code == 409
    denied = request(
        client,
        "post",
        f"applications/{app['id']}/rebase",
        {"confirm": False},
        revision=app["revision"],
    )
    assert denied.status_code == 409
    rebased = request(
        client,
        "post",
        f"applications/{app['id']}/rebase",
        {"confirm": True},
        revision=app["revision"],
    )
    assert rebased.status_code == 200, rebased.content
    current = rebased.json()
    assert not current["source_changed"] and not current["can_rebase"]
    assert current["scholarship_version_id"] != app["scholarship_version_id"]
    assert current["round_key"] == app["round_key"] and current["missing_count"] == 1
    assert current["requirements"][0]["label"] == "New reviewed document"
    assert current["requirements"][0]["version_id"] is None
    assert ApplicationRequirement.objects.filter(application_id=app["id"]).count() == 3
    history = client.get(f"/api/v1/applications/{app['id']}/history").json()["items"]
    assert history[:-1] == before
    assert history[-1]["kind"] == "REBASE" and history[-1]["manifest_snapshot"] == []
    assert history[-1]["scholarship_version_id"] == current["scholarship_version_id"]
    assert (
        request(
            client,
            "post",
            f"applications/{app['id']}/rebase",
            {"confirm": True},
            revision=current["revision"],
        ).status_code
        == 409
    )


def test_new_distinct_reviewed_round_requires_new_tracker(catalog):
    moderator, source, prior = catalog
    from test_catalog import candidate_payload, moderate, post

    response = post(
        moderator,
        f"admin/scholarships/{prior['id']}/versions",
        candidate_payload(
            source,
            rounds=[
                {"kind": "UNKNOWN", "label": "2027 reviewed round"},
                {"kind": "UNKNOWN", "label": "2028 reviewed round"},
            ],
        ),
        revision=prior["revision"],
    )
    assert response.status_code == 200
    reviewed = moderate(moderator, response.json())
    assert reviewed.status_code == 200
    client, _ = signed_client()
    first = create_application(client, reviewed.json(), index=0)
    second = create_application(client, reviewed.json(), index=1)
    assert first["id"] != second["id"] and first["round_key"] != second["round_key"]
    assert move(client, first, "WITHDRAWN").status_code == 200
    options = client.get(
        "/api/v1/applications/round-options", {"scholarship_id": prior["id"]}
    ).json()
    assert (
        request(
            client,
            "post",
            "applications",
            {"scholarship_id": prior["id"], "round_key": options["items"][0]["round_key"]},
        ).status_code
        == 409
    )
    page = client.get("/api/v1/applications", {"page": 1, "page_size": 1}).json()
    next_page = client.get("/api/v1/applications", {"page": 2, "page_size": 1}).json()
    assert page["total"] == next_page["total"] == 2
    assert len(page["items"]) == len(next_page["items"]) == 1
    assert page["items"][0]["id"] != next_page["items"][0]["id"]
    assert page["counts"]["WITHDRAWN"] == 1 and page["counts"]["PREPARING"] == 1
    assert client.get("/api/v1/applications", {"page_size": 101}).status_code == 400
