# Django
from django.core.management.base import BaseCommand

# Pap Stats
from papstats.tasks import process_afat_data_task, run_last_month_task


class Command(BaseCommand):
    help = "Aggregate monthly stats"

    def add_arguments(self, parser):
        parser.add_argument(
            "--month", type=int, help="Month for which to aggregate stats"
        )
        parser.add_argument(
            "--year", type=int, help="Year for which to aggregate stats"
        )

    def handle(self, *args, **options):
        month = options["month"]
        year = options["year"]
        process_afat_data_task.delay(month, year)
        # run_last_month_task.delay()
        self.stdout.write(
            self.style.SUCCESS("Successfully started task to process afat data")
        )
