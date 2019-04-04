from django.contrib import admin
from .models import InfluxMigration, MigrationSlot

class InfluxMigrationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'source_host',
        'destination_host'
    ]

admin.site.register(InfluxMigration, InfluxMigrationAdmin)