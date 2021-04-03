# Generated by Django 3.1.7 on 2021-03-29 13:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("authentik_flows", "0016_auto_20201202_1307"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="flow",
            options={
                "permissions": [
                    ("export_flow", "Can export a Flow"),
                    ("view_flow_cache", "View Flow's cache metrics"),
                    ("clear_flow_cache", "Clear Flow's cache metrics"),
                ],
                "verbose_name": "Flow",
                "verbose_name_plural": "Flows",
            },
        ),
    ]