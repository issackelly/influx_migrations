from django.db import models
from django.utils import timezone
from influxdb import InfluxDBClient
import datetime
import yaml
import pytz
import re

class InfluxMigration(models.Model):
    source_host = models.CharField(max_length=128, default="localhost")
    source_port = models.PositiveIntegerField(default=8086)
    source_db = models.CharField(max_length=128, default="default")
    source_measurement = models.CharField(max_length=128, default="default")
    destination_host = models.CharField(max_length=128, default="localhost")
    destination_port = models.PositiveIntegerField(default=8086)
    destination_db = models.CharField(max_length=128, default="default_dest")
    destination_measurement = models.CharField(max_length=128, default="default")
    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)
    slot_seconds = models.PositiveIntegerField(default=5 * 60)

    translation_yaml = models.TextField()
    _translation = None

    @property
    def translation(self):
        if self._translation:
            return self._translation
        else:
            self._translation = yaml.load(self.translation_yaml)["translation"]
        return self._translation

    def save(self, *args, **kwargs):
        self.translation
        super().save(*args, **kwargs)

    def build_slots(self):
        # Deletes all old slots
        # Make new slots based on start (or Jan 1, 2015), end (or now) and startseconds
        self.slots.all().delete()

        if not self.start:
            self.start = datetime.datetime(year=2015, month=1, day=1, tz=pytz.UTC)

        if not self.end:
            self.end = timezone.now()

        self.save()

        cursor = self.start
        while cursor < self.end:
            end = cursor + datetime.timedelta(seconds=self.slot_seconds)
            MigrationSlot.objects.create(
                migration=self,
                start=cursor,
                end=end,
            )
            cursor = end


class MigrationSlot(models.Model):
    migration = models.ForeignKey(InfluxMigration, related_name="slots", on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    confirmed_success = models.DateTimeField(default=None, blank=True, null=True)

    def run(self):
        s_cli = InfluxDBClient(self.migration.source_host, self.migration.source_port)
        s_cli.switch_database(self.migration.source_db)
        d_cli = InfluxDBClient(self.migration.destination_host, self.migration.destination_port)
        d_cli.create_database(self.migration.destination_db)
        d_cli.switch_database(self.migration.destination_db)

        start_ns = int(self.start.timestamp() * 1_000_000_000)
        end_ns = int(self.end.timestamp() * 1_000_000_000)
        query = f"SELECT * FROM \"{self.migration.source_measurement}\" WHERE time > {start_ns} and time <= {end_ns}"
        input_results = s_cli.query(query)
        if input_results:
            for result in input_results.get_points():
                output_point = {
                    "measurement": self.migration.destination_measurement,
                    "time": result.pop("time"),
                    "fields": {}
                }
                for key, value in result.items():
                    # Run the Drop Key Step
                    if key in self.migration.translation['drop_keys']:
                        continue

                    # Run the Key Change Step
                    for key_change in self.migration.translation['key_changes']:
                        if re.search(key_change['source_regex'], key):
                            to_eval = 'f\"'+key_change['destination_eval']+'\"'
                            new_key = eval(to_eval)
                            key = new_key

                    if value:
                        output_point["fields"][key] = float(value)

                    # Run the Value Evals Step, which has the possibility of overwriting the old key
                    for value_eval in self.migration.translation['value_evals']:
                        if key == value_eval['key']:
                            to_eval = 'f\"'+value_eval['eval_value']+'\"'
                            new_val = eval(eval(to_eval))
                            dest_key = value_eval['destination_key']

                            if new_val:
                                output_point["fields"][dest_key] = float(new_val)

                d_cli.write_points([output_point])
