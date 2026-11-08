"""End-to-end checks of the demo project in tests/demo."""

import pytest
from django.core.management import call_command
from freezegun import freeze_time

from django_db_tenants import tenant_context
from notes.models import Note
from notes.tasks import notes_per_tenant, purge_old_notes
from testutils.databases import selected_backend
from testutils.factories import NoteFactory, UserFactory
from testutils.tenants import tenant_login


@pytest.mark.django_db
def test_control_plane_home(client):
    response = client.get("/", HTTP_HOST="control.test")
    assert b"Control plane" in response.content


def test_tenant_home(client, acme):
    response = client.get("/", HTTP_HOST="acme.test")
    assert b"Welcome to ACME" in response.content


def test_notes_require_login(client, acme):
    response = client.get("/notes/", HTTP_HOST="acme.test")
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


def test_password_login_uses_tenant_users(client, acme, globex):
    with tenant_context(acme):
        UserFactory.create(username="alice")

    form = {"username": "alice", "password": "pw"}
    assert client.post("/accounts/login/", form, HTTP_HOST="acme.test").status_code == 302
    assert client.post("/accounts/login/", form, HTTP_HOST="globex.test").status_code == 200  # form error


def test_notes_are_stored_per_tenant(client, acme, globex):
    with tenant_context(acme):
        alice = UserFactory.create()
    tenant_login(client, acme, alice)

    response = client.post("/notes/", {"title": "Hello", "body": "from acme"}, HTTP_HOST="acme.test")

    assert response.status_code == 302
    assert b"Hello" in client.get("/notes/", HTTP_HOST="acme.test").content
    with tenant_context(acme):
        assert Note.objects.get().author == alice
    with tenant_context(globex):
        assert not Note.objects.exists()


def test_purge_old_notes(acme):
    with freeze_time("2026-01-01"), tenant_context(acme):
        NoteFactory.create_batch(2)
    with freeze_time("2026-01-25"), tenant_context(acme):
        NoteFactory.create()

    with freeze_time("2026-02-10"):
        assert purge_old_notes("acme", days=30) == 2
    with tenant_context(acme):
        assert Note.objects.count() == 1


def test_notes_report(acme, globex, capsys):
    with tenant_context(globex):
        NoteFactory.create_batch(3)

    assert notes_per_tenant() == {"acme": 0, "globex": 3}
    call_command("notes_report")
    assert capsys.readouterr().out == "acme: 0\nglobex: 3\n"


@pytest.mark.skipif(selected_backend() != "sqlite", reason="the demo seeds SQLite files")
@pytest.mark.django_db
def test_seed_demo(settings, tmp_path):
    settings.VAR_DIR = tmp_path
    call_command("seed_demo", stdout=None)
    call_command("seed_demo", stdout=None)  # idempotent
    assert sorted(p.name for p in tmp_path.iterdir()) == ["acme.sqlite3", "globex.sqlite3"]
