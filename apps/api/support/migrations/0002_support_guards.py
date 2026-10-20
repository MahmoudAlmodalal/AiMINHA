from typing import Any

from django.db import migrations

DEFAULT_TARGETS = {"CRITICAL": 240, "HIGH": 480, "NORMAL": 1440, "LOW": 2880}


def initial_policy(apps: Any, schema_editor: Any) -> None:
    """Seed the sourced default working calendar and its head pointer."""
    calendar = apps.get_model("support", "SupportCalendar")
    head = apps.get_model("support", "SupportCalendarHead")
    if head.objects.filter(pk=1).exists():
        return
    policy = calendar.objects.create(
        version=1,
        timezone="Asia/Hebron",
        working_weekdays=[0, 1, 2, 3, 6],
        opens_local="09:00",
        closes_local="17:00",
        holidays=[],
        targets=DEFAULT_TARGETS,
        ai_daily_messages=5,
        closure_days=7,
        reopen_days=14,
        rating_edit_days=7,
        warning_percent=80,
        reason="Sourced default support calendar and lifecycle windows (OQ-008/009/010).",
    )
    head.objects.create(id=1, policy=policy)


GUARDS = """
CREATE FUNCTION support_forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable support evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER support_event_immutable BEFORE UPDATE OR DELETE ON support_ticketevent
FOR EACH ROW EXECUTE FUNCTION support_forbid_mutation();
CREATE TRIGGER support_calendar_immutable BEFORE UPDATE OR DELETE ON support_supportcalendar
FOR EACH ROW EXECUTE FUNCTION support_forbid_mutation();
CREATE TRIGGER support_message_immutable BEFORE DELETE ON support_ticketmessage
FOR EACH ROW EXECUTE FUNCTION support_forbid_mutation();
CREATE FUNCTION support_guard_ticket() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN
    RAISE EXCEPTION 'immutable ticket owner' USING ERRCODE='23514';
  END IF;
  IF NEW.access_id IS DISTINCT FROM OLD.access_id THEN
    RAISE EXCEPTION 'immutable ticket identity' USING ERRCODE='23514';
  END IF;
  IF NEW.row_version < OLD.row_version THEN
    RAISE EXCEPTION 'ticket revision never moves backwards' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER support_ticket_guard BEFORE UPDATE ON support_ticket
FOR EACH ROW EXECUTE FUNCTION support_guard_ticket();
"""


class Migration(migrations.Migration):
    dependencies = [("support", "0001_initial")]
    operations = [
        migrations.RunPython(initial_policy, migrations.RunPython.noop),
        # Forward-only: never automatically remove evidence guards from populated data.
        migrations.RunSQL(GUARDS),
    ]
