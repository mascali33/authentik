# Generated by Django 2.2.6 on 2019-10-07 14:06

import uuid

import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import passbook.core.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True, max_length=254, verbose_name="email address"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("name", models.TextField()),
                ("password_change_date", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "abstract": False,
            },
            managers=[("objects", django.contrib.auth.models.UserManager()),],
        ),
        migrations.CreateModel(
            name="Policy",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.TextField(blank=True, null=True)),
                (
                    "action",
                    models.CharField(
                        choices=[("allow", "allow"), ("deny", "deny")], max_length=20
                    ),
                ),
                ("negate", models.BooleanField(default=False)),
                ("order", models.IntegerField(default=0)),
                ("timeout", models.IntegerField(default=30)),
            ],
            options={"abstract": False,},
        ),
        migrations.CreateModel(
            name="PolicyModel",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "policies",
                    models.ManyToManyField(blank=True, to="passbook_core.Policy"),
                ),
            ],
            options={"abstract": False,},
        ),
        migrations.CreateModel(
            name="PropertyMapping",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.TextField()),
            ],
            options={
                "verbose_name": "Property Mapping",
                "verbose_name_plural": "Property Mappings",
            },
        ),
        migrations.CreateModel(
            name="DebugPolicy",
            fields=[
                (
                    "policy_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="passbook_core.Policy",
                    ),
                ),
                ("result", models.BooleanField(default=False)),
                ("wait_min", models.IntegerField(default=5)),
                ("wait_max", models.IntegerField(default=30)),
            ],
            options={
                "verbose_name": "Debug Policy",
                "verbose_name_plural": "Debug Policies",
            },
            bases=("passbook_core.policy",),
        ),
        migrations.CreateModel(
            name="Factor",
            fields=[
                (
                    "policymodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="passbook_core.PolicyModel",
                    ),
                ),
                ("name", models.TextField()),
                ("slug", models.SlugField(unique=True)),
                ("order", models.IntegerField()),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={"abstract": False,},
            bases=("passbook_core.policymodel",),
        ),
        migrations.CreateModel(
            name="Source",
            fields=[
                (
                    "policymodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="passbook_core.PolicyModel",
                    ),
                ),
                ("name", models.TextField()),
                ("slug", models.SlugField()),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={"abstract": False,},
            bases=("passbook_core.policymodel",),
        ),
        migrations.CreateModel(
            name="Provider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "property_mappings",
                    models.ManyToManyField(
                        blank=True, default=None, to="passbook_core.PropertyMapping"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Nonce",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "expires",
                    models.DateTimeField(
                        default=passbook.core.models.default_token_duration
                    ),
                ),
                ("expiring", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Nonce", "verbose_name_plural": "Nonces",},
        ),
        migrations.CreateModel(
            name="Invitation",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("expires", models.DateTimeField(blank=True, default=None, null=True)),
                ("fixed_username", models.TextField(blank=True, default=None)),
                ("fixed_email", models.TextField(blank=True, default=None)),
                ("needs_confirmation", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Invitation",
                "verbose_name_plural": "Invitations",
            },
        ),
        migrations.CreateModel(
            name="Group",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=80, verbose_name="name")),
                (
                    "tags",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="passbook_core.Group",
                    ),
                ),
            ],
            options={"unique_together": {("name", "parent")},},
        ),
        migrations.AddField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(to="passbook_core.Group"),
        ),
        migrations.AddField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.Permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.CreateModel(
            name="UserSourceConnection",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="passbook_core.Source",
                    ),
                ),
            ],
            options={"unique_together": {("user", "source")},},
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                (
                    "policymodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="passbook_core.PolicyModel",
                    ),
                ),
                ("name", models.TextField()),
                ("slug", models.SlugField()),
                ("launch_url", models.URLField(blank=True, null=True)),
                ("icon_url", models.TextField(blank=True, null=True)),
                ("skip_authorization", models.BooleanField(default=False)),
                (
                    "provider",
                    models.OneToOneField(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_DEFAULT,
                        to="passbook_core.Provider",
                    ),
                ),
            ],
            options={"abstract": False,},
            bases=("passbook_core.policymodel",),
        ),
        migrations.AddField(
            model_name="user",
            name="sources",
            field=models.ManyToManyField(
                through="passbook_core.UserSourceConnection", to="passbook_core.Source"
            ),
        ),
    ]
