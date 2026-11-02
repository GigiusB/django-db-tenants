from django.core.management.base import BaseCommand

from notes.tasks import notes_per_tenant


class Command(BaseCommand):
    help = "Print the number of notes stored in each active tenant database."

    def handle(self, *args, **options) -> None:
        for slug, count in sorted(notes_per_tenant().items()):
            self.stdout.write(f"{slug}: {count}")
