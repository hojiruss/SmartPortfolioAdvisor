from django.core.management.base import BaseCommand

from assessment.seed_data import seed_questionnaire


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--questionnaire-version', type=int, default=1, dest='questionnaire_version')

    def handle(self, *args, **options):
        created = seed_questionnaire(version=options['questionnaire_version'])
        self.stdout.write(self.style.SUCCESS(f'{created} سوال جدید ساخته شد'))
