# Generated by Django 4.1.9 on 2023-05-17 13:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_emailaddress_unique_email_verified_per_user"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="emailaddress",
            constraint=models.UniqueConstraint(
                condition=models.Q(("verified_at", None)),
                fields=("user",),
                name="unique_email_not_verified_per_user",
                violation_error_message="Un utilisateur ne peut pas avoir plusieurs e-mails non vérifiés.",
            ),
        ),
    ]