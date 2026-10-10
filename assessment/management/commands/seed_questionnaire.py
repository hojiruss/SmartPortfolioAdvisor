from django.core.management.base import BaseCommand

from assessment.seed_data import seed_questionnaire


class Command(BaseCommand):
    help = 'ساخت پرسش‌نامه‌ی ارزیابی ریسک (نسخه‌ی اول) طبق PRD. اجرای دوباره، چیزی را تغییر نمی‌دهد.'

    def add_arguments(self, parser):
        parser.add_argument('--version', type=int, default=1)

    def handle(self, *args, **options):
        created = seed_questionnaire(version=options['version'])
        self.stdout.write(self.style.SUCCESS(f'{created} سوال جدید ساخته شد'))
