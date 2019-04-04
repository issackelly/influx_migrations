InfluxDB Migration Tool
-----------------------


This tool will allow you to plan and run migrations against InfluxDB

IMPORTANT: This does not currently take into account tags at all

IMPORTANT: This is very much an Alpha product, use at your own risk

Features:

* Cursor based migrations
    * Set your source and destination influx settings
    * Set a cursor size, start and end time
    * Iterate over your dataset and run your migration
* Cross-Database (Intra or Cross Host) Migration
    * Key Dropping
    * Key Renaming
    * Value Changing
* Intra Database Migrations
    * Key Replication (keep old points, keep duplicate under different key name)
    * Change Value via function

* Python (with Django) based Administration
    * Web UI (django admin) for planning and browsing changes
    * Local (Sqlite3) or other Django supported database for tracking migrations and progress

Non-Features:

* Intra-Database Key Dropping
* Tags


.. code-block:: bash

    pip install https://github.com/issackelly/influx_migrations/tarball/master
    cd influx_migrations
    python manage.py runserver
    # Go to http://localhost:8000/admin
    # Log in as admin/admin
    # Plan a migration


Plan a Migration
~~~~~~~~~~~~~~~~

Start a new influx migration in the admin
Fill in the source and destination information
Fill in the start and end information.
It will start in 2015 and end (now) if you don't choose

The default slot seconds are 300 (5 minutes)

Run a Migration
~~~~~~~~~~~~~~~

Migrations are currently run manually.

.. code-block:: python

    python manage.py shell
    from influx_migrations.models import InfluxMigration
    mig = InfluxMigration.objects.get(id=1)
    mig.build_slots()
    for slot in mig.slots.all():
        slot.run()


A clever migrator could run migrations in parallel, or schedule them.

Advanced Use
~~~~~~~~~~~~

Install this as an application in your own django environment by adding it to `installed_apps`, migrating, and using your own database.