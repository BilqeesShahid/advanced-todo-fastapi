"""
Main entry point for the Recurring Task Service.

This service consumes task.completed events and creates next occurrences based on recurrence rules.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

from .consumers.task_completed_consumer import TaskCompletedConsumer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the recurring task service."""
    logger.info("Starting Recurring Task Service...")

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

    # Create consumer instance
    consumer = TaskCompletedConsumer(database_url)

    # Check if running in development mode (without Dapr)
    if os.getenv("ENVIRONMENT") == "development":
        logger.info("Running in development mode...")
        consumer.run_dev_mode()
    else:
        # Start the consumer to listen for events
        await consumer.start_consumer()

if __name__ == "__main__":
    asyncio.run(main())