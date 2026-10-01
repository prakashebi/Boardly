from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(db_index=True, max_length=255, unique=True)),
                ('username', models.CharField(db_index=True, max_length=100, unique=True)),
                ('hashed_password', models.CharField(max_length=255)),
                ('role', models.CharField(choices=[('admin', 'Admin'), ('member', 'Member'), ('viewer', 'Viewer')], default='member', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'users',
            },
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('entity_type', models.CharField(db_index=True, max_length=100)),
                ('title', models.CharField(max_length=500)),
                ('description', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('archived', 'Archived')], db_index=True, default='active', max_length=20)),
                ('metadata', models.JSONField(blank=True, default=dict, null=True)),
                ('owner_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'entities',
            },
        ),
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(db_index=True, max_length=100)),
                ('actor_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('entity_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('entity_type', models.CharField(blank=True, max_length=100, null=True)),
                ('payload', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'audit_events',
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('entity_id', models.UUIDField(db_index=True)),
                ('user_id', models.UUIDField(db_index=True)),
                ('role', models.CharField(choices=[('editor', 'Editor'), ('viewer', 'Viewer')], default='viewer', max_length=20)),
                ('invited_by', models.UUIDField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'memberships',
                'unique_together': {('entity_id', 'user_id')},
            },
        ),
    ]
