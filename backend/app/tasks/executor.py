"""
Refactored Celery Tasks using ExecutorService
File: backend/app/tasks/executor.py
"""

from celery import Celery
from datetime import datetime, timezone
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.script import Script
from app.models.execution import ExecutionStatus, Execution
from app.services.secret_service import SecretService
from app.services.executor_service import executor_service
from app.core.websocket_bridge import websocket_bridge

logger = logging.getLogger(__name__)

# Celery app configuration
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
)


def send_log(execution_id: int, log_type: str, content: str):
    """Send log via Redis Pub/Sub"""
    try:
        websocket_bridge.publish_log(execution_id, log_type, content)
    except Exception as e:
        logger.error(f"[REDIS-LOG] Error: {e}")


def send_status(execution_id: int, status: str, metadata: dict = None):
    """Send status update via Redis Pub/Sub"""
    try:
        websocket_bridge.publish_status(execution_id, status, metadata)
    except Exception as e:
        logger.error(f"[REDIS-STATUS] Error: {e}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_script_task(self, execution_id: int):
    """
    Execute script using unified ExecutorService
    
    This task:
    1. Retrieves execution and script from database
    2. Fetches required secrets
    3. Executes script in Docker container
    4. Streams real-time logs via WebSocket
    5. Updates execution status
    
    Args:
        execution_id: ID of the execution record
    """
    db = SessionLocal()
    
    try:
        # Fetch execution
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error(f"[TASK] Execution {execution_id} not found")
            return {"error": "Execution not found"}
        
        # Fetch script
        script = db.query(Script).filter(Script.id == execution.script_id).first()
        if not script:
            execution.status = ExecutionStatus.FAILED
            execution.error = "Script not found"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            send_status(execution.id, "failed", {"error": "Script not found"})
            return {"error": "Script not found"}
        
        logger.info(
            f"[TASK] Starting execution {execution_id} for script: {script.name} (type: {script.script_type})",
            extra={"execution_id": execution_id, "script_id": script.id}
        )
        
        # Update status to RUNNING
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Send initial messages
        send_status(execution.id, "running", {
            "started_at": execution.started_at.isoformat()
        })
        send_log(execution.id, "info", f"🚀 Starting: {script.name}\n")
        send_log(execution.id, "info", f"📝 Type: {script.script_type.value}\n")
        
        # Fetch secrets for script
        secrets_dict = SecretService.get_secrets_for_script(
            db=db,
            script_id=script.id,
            execution_id=execution.id,
            username=execution.executed_by
        )
        
        if secrets_dict:
            send_log(execution.id, "info", f"🔐 Injected {len(secrets_dict)} secret(s)\n")
        
        # Prepare environment variables
        env_vars = {}
        
        # Add execution parameters
        if execution.parameters:
            for key, value in execution.parameters.items():
                env_vars[key] = str(value) if not isinstance(value, str) else value
        
        # Add secrets
        if secrets_dict:
            env_vars.update(secrets_dict)
        
        # Get timeout from parameters or use default
        timeout = 300  # Default 5 minutes
        if execution.parameters and "timeout" in execution.parameters:
            try:
                timeout = int(execution.parameters["timeout"])
                timeout = max(10, min(timeout, 3600))  # Clamp between 10s and 1h
            except (ValueError, TypeError):
                logger.warning(f"Invalid timeout value, using default: {timeout}")
        
        # Create log callback for real-time streaming
        def log_callback(log_type: str, content: str):
            send_log(execution.id, log_type, content)
        
        # Execute script using ExecutorService
        send_log(execution.id, "info", f"⚙️  Executing {script.script_type.value} script in Docker...\n")
        send_log(execution.id, "info", "─" * 50 + "\n")
        
        exit_code, stdout, stderr = executor_service.execute(
            script_type=script.script_type,
            content=script.content,
            env_vars=env_vars,
            timeout=timeout,
            log_callback=log_callback
        )
        
        send_log(execution.id, "info", "\n" + "─" * 50 + "\n")
        
        # Update execution with results
        execution.output = stdout
        execution.error = stderr if exit_code != 0 else None
        execution.status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
        execution.completed_at = datetime.now(timezone.utc)
        
        db.commit()
        
        # Send completion status
        send_status(execution.id, execution.status.value, {
            "completed_at": execution.completed_at.isoformat(),
            "exit_code": exit_code
        })
        
        if exit_code == 0:
            send_log(execution.id, "info", "✅ Completed successfully\n")
            logger.info(f"[TASK] Execution {execution_id} completed successfully")
        else:
            send_log(execution.id, "error", f"❌ Failed (exit code: {exit_code})\n")
            logger.warning(f"[TASK] Execution {execution_id} failed with exit code {exit_code}")
        
        return {
            "execution_id": execution_id,
            "status": execution.status.value,
            "exit_code": exit_code
        }
        
    except Exception as e:
        logger.error(f"[TASK] Fatal error in execution {execution_id}: {e}", exc_info=True)
        
        # Update execution status on error
        try:
            if execution:
                execution.status = ExecutionStatus.FAILED
                execution.error = f"Internal error: {str(e)}"
                execution.completed_at = datetime.now(timezone.utc)
                db.commit()
                
                send_status(execution.id, "failed", {"error": str(e)})
                send_log(execution.id, "error", f"❌ Fatal Error: {str(e)}\n")
        except Exception as db_error:
            logger.error(f"[TASK] Failed to update execution status: {db_error}")
        
        # Retry task if retriable error
        if self.request.retries < self.max_retries:
            logger.info(f"[TASK] Retrying execution {execution_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60)
        
        return {"error": str(e), "execution_id": execution_id}
        
    finally:
        db.close()


@celery_app.task
def cleanup_old_containers_task():
    """
    Scheduled task to cleanup old Docker containers
    Should be run periodically via Celery Beat
    """
    try:
        count = executor_service.cleanup_old_containers(max_age_hours=24)
        logger.info(f"[CLEANUP] Removed {count} old containers")
        return {"removed": count, "status": "success"}
    except Exception as e:
        logger.error(f"[CLEANUP] Error during cleanup: {e}")
        return {"error": str(e), "status": "failed"}


@celery_app.task
def healthcheck_task():
    """
    Healthcheck task to verify Celery workers are responding
    """
    return {
        "status": "healthy",
        "worker": "online",
        "docker_available": executor_service.is_available()
    }


# Celery Beat schedule (if using)
celery_app.conf.beat_schedule = {
    'cleanup-old-containers': {
        'task': 'app.tasks.executor.cleanup_old_containers_task',
        'schedule': 3600.0,  # Run every hour
    },
}