"""Phase 5: Advanced Task Features

Revision ID: 001
Revises:
Create Date: 2026-02-04 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None  # This is the first migration
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for advanced task features to the existing task table
    # Using conditional additions in case they already exist

    # Check if columns exist before adding them
    conn = op.get_bind()

    # Add priority column if it doesn't exist
    try:
        op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'medium' CHECK (priority IN ('high','medium','low'))")
    except:
        # If the ALTER TABLE fails, try a different approach
        op.add_column('task', sa.Column('priority', sa.Text, server_default='medium'))

    # Add due_date column if it doesn't exist
    try:
        op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ")
    except:
        op.add_column('task', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))

    # Add tags column if it doesn't exist
    try:
        op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS tags TEXT[]")
    except:
        op.add_column('task', sa.Column('tags', postgresql.ARRAY(sa.Text), nullable=True))

    # Add recurrence column if it doesn't exist
    try:
        op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS recurrence TEXT")
    except:
        op.add_column('task', sa.Column('recurrence', sa.Text, nullable=True))

    # Add recurrence_rule column if it doesn't exist
    try:
        op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS recurrence_rule TEXT")
    except:
        op.add_column('task', sa.Column('recurrence_rule', sa.Text, nullable=True))

    # Add next_occurrence column if it doesn't exist
    try:
        op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS next_occurrence TIMESTAMPTZ")
    except:
        op.add_column('task', sa.Column('next_occurrence', sa.DateTime(timezone=True), nullable=True))

    # Create indexes for improved performance
    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON task(priority)")
    except:
        # If index exists, ignore
        pass

    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON task(due_date)")
    except:
        pass

    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_next_occurrence ON task(next_occurrence)")
    except:
        pass

    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tags ON task USING GIN (tags)")
    except:
        pass

    # Create events table for event sourcing
    try:
        op.create_table('event',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('event_id', sa.String(length=36), nullable=False),
            sa.Column('type', sa.String(length=50), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('source', sa.String(length=100), nullable=False),
            sa.Column('data', postgresql.JSONB(), nullable=False),
            sa.Column('processed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('event_id')
        )

        # Create indexes for efficient querying
        op.create_index('idx_events_type', 'event', ['type'])
        op.create_index('idx_events_timestamp', 'event', ['timestamp'])
        op.create_index('idx_events_processed', 'event', ['processed'])
        op.create_index('idx_events_source', 'event', ['source'])
    except:
        # If table exists, ignore
        pass

    # Create notifications table for reminders
    try:
        op.create_table('notification',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('task_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(length=100), nullable=False),
            sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('sent_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
            sa.Column('delivery_attempts', sa.Integer(), server_default='0', nullable=False),
            sa.Column('channel', sa.String(length=20), nullable=False),
            sa.Column('message_content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for efficient scheduling and querying
        op.create_index('idx_notifications_scheduled_time', 'notification', ['scheduled_time', 'status'])
        op.create_index('idx_notifications_task_id', 'notification', ['task_id'])
        op.create_index('idx_notifications_user_id', 'notification', ['user_id'])
        op.create_index('idx_notifications_status', 'notification', ['status'])
    except:
        # If table exists, ignore
        pass


def downgrade():
    # Drop indexes
    try:
        op.drop_index('idx_notifications_status', table_name='notification')
        op.drop_index('idx_notifications_user_id', table_name='notification')
        op.drop_index('idx_notifications_task_id', table_name='notification')
        op.drop_index('idx_notifications_scheduled_time', table_name='notification')
    except:
        pass

    # Drop notifications table
    try:
        op.drop_table('notification')
    except:
        pass

    # Drop indexes
    try:
        op.drop_index('idx_events_source', table_name='event')
        op.drop_index('idx_events_processed', table_name='event')
        op.drop_index('idx_events_timestamp', table_name='event')
        op.drop_index('idx_events_type', table_name='event')
    except:
        pass

    # Drop events table
    try:
        op.drop_table('event')
    except:
        pass

    # Drop indexes
    try:
        op.execute("DROP INDEX IF EXISTS idx_tasks_tags")
        op.execute("DROP INDEX IF EXISTS idx_tasks_next_occurrence")
        op.execute("DROP INDEX IF EXISTS idx_tasks_due_date")
        op.execute("DROP INDEX IF EXISTS idx_tasks_priority")
    except:
        pass

    # Remove the new columns
    try:
        op.execute("ALTER TABLE task DROP COLUMN IF EXISTS next_occurrence")
        op.execute("ALTER TABLE task DROP COLUMN IF EXISTS recurrence_rule")
        op.execute("ALTER TABLE task DROP COLUMN IF EXISTS recurrence")
        op.execute("ALTER TABLE task DROP COLUMN IF EXISTS tags")
        op.execute("ALTER TABLE task DROP COLUMN IF EXISTS due_date")
        op.execute("ALTER TABLE task DROP COLUMN IF EXISTS priority")
    except:
        # Try alternate approach if direct ALTER fails
        op.drop_column('task', 'next_occurrence')
        op.drop_column('task', 'recurrence_rule')
        op.drop_column('task', 'recurrence')
        op.drop_column('task', 'tags')
        op.drop_column('task', 'due_date')
        op.drop_column('task', 'priority')