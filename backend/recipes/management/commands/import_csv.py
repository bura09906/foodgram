import csv
import os

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.import_data()
        self.stdout.write(self.style.SUCCESS('Data imported successfully'))

    def import_data(self):
        Ingredient.objects.all().delete()
        current_dir = os.path.dirname(__file__)
        csv_file_path = os.path.join(current_dir, 'ingredients.csv')
        with open(csv_file_path, 'r', encoding='utf8') as file:
            reader = csv.reader(file)
            for data in reader:
                name, measurement_unit = data
                Ingredient.objects.create(
                    name=name, measurement_unit=measurement_unit
                )
                self.stdout.write(
                    f"Ингредиент {name} ({measurement_unit}) добавлен"
                )
