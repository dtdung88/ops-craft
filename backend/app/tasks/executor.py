import os
import sys
import asyncio
import subprocess
import threading
import logging
from celery import Celery
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.script import Script
from app.models.execution import ExecutionStatus, Execution
from app.services.SecretService import SecretService
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)


def send_websocket_log_sync(execution_id: int, log_type: str, content: str):
    """Synchronous wrapper to send WebSocket logs"""
    try:
        logger.info(f"[WS-LOG] Execution {execution_id}, Type: {log_type}, Content: {content[:50]}...")
        
        # Import here to avoid circular imports
        from app.api.routes.websocket import manager
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(manager.broadcast_log(execution_id, log_type, content))
            logger.info(f"[WS-LOG] Successfully sent to execution {execution_id}")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"[WS-LOG] Failed to send WebSocket log: {e}", exc_info=True)


def send_websocket_status_sync(execution_id: int, status: str, metadata: dict = None):
    """Synchronous wrapper to send WebSocket status"""
    try:
        logger.info(f"[WS-STATUS] Execution {execution_id}, Status: {status}")
        
        from app.api.routes.websocket import manager
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(manager.broadcast_status(execution_id, status, metadata))
            logger.info(f"[WS-STATUS] Successfully sent to execution {execution_id}")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"[WS-STATUS] Failed to send WebSocket status: {e}", exc_info=True)


@celery_app.task
def execute_script_task(execution_id: int):
    """Celery task to execute a script with real-time WebSocket streaming."""
    
    logger.info(f"[TASK] Starting execution task for ID: {execution_id}")
    
    db = SessionLocal()
    
    try:
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error(f"[TASK] Execution {execution_id} not found")
            return
        
        script = db.query(Script).filter(Script.id == execution.script_id).first()
        if not script:
            logger.error(f"[TASK] Script {execution.script_id} not found")
            execution.status = ExecutionStatus.FAILED
            execution.error = "Script not found"
            db.commit()
            return
        
        logger.info(f"[TASK] Executing script: {script.name} (ID: {script.id})")
        
        # Update status to running
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Send initial status
        send_websocket_status_sync(execution.id, "running", {"started_at": execution.started_at.isoformat()})
        send_websocket_log_sync(execution.id, "info", f"🚀 Starting execution of script: {script.name}\n")
        
        # Get secrets
        secrets_dict = SecretService.get_secrets_for_script(
            db=db,
            script_id=script.id,
            execution_id=execution.id,
            user_id=None,
            username=execution.executed_by
        )
        
        if secrets_dict:
            logger.info(f"[TASK] Injected {len(secrets_dict)} secrets")
            send_websocket_log_sync(execution.id, "info", f"🔐 Injected {len(secrets_dict)} secret(s)\n")
        
        # Prepare environment
        env_vars = os.environ.copy()
        if execution.parameters:
            for key, value in execution.parameters.items():
                env_vars[key] = str(value) if not isinstance(value, str) else value
        env_vars.update(secrets_dict or {})
        
        # Execute
        try:
            send_websocket_log_sync(execution.id, "info", f"⚙️  Executing {script.script_type} script...\n")
            send_websocket_log_sync(execution.id, "info", "─" * 50 + "\n")
            
            logger.info(f"[TASK] Starting script execution...")
            
            exit_code, stdout, stderr = execute_bash_with_streaming(
                script_content=script.content,
                env_vars=env_vars,
                execution_id=execution.id,
                timeout=300
            )
            
            logger.info(f"[TASK] Script completed with exit code: {exit_code}")
            
            send_websocket_log_sync(execution.id, "info", "─" * 50 + "\n")
            
            execution.output = stdout
            execution.error = stderr if exit_code != 0 else None
            execution.status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
            
            if exit_code == 0:
                send_websocket_log_sync(execution.id, "info", f"✅ Execution completed successfully\n")
            else:
                send_websocket_log_sync(execution.id, "error", f"❌ Execution failed (exit code: {exit_code})\n")
            
        except Exception as e:
            logger.error(f"[TASK] Execution error: {e}", exc_info=True)
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Execution error: {str(e)}"
            execution.output = None
            send_websocket_log_sync(execution.id, "error", f"❌ Error: {str(e)}\n")
        
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Send final status
        send_websocket_status_sync(
            execution.id, 
            execution.status.value,
            {"completed_at": execution.completed_at.isoformat()}
        )
        
        logger.info(f"[TASK] Task completed for execution {execution_id}")
        
    except Exception as e:
        logger.error(f"[TASK] Fatal error: {e}", exc_info=True)
        if execution:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Task error: {str(e)}"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
        
    finally:
        db.close()


def execute_bash_with_streaming(script_content: str, env_vars: dict, execution_id: int, timeout: int = 300):
    """Execute bash script with real-time streaming output"""
    import tempfile
    
    logger.info(f"[EXEC] Creating temporary script file...")
    
    # Create temp script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    logger.info(f"[EXEC] Script path: {script_path}")
    
    try:
        os.chmod(script_path, 0o755)
        
        logger.info(f"[EXEC] Starting subprocess...")
        
        # Start process
        process = subprocess.Popen(
            ['bash', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env_vars,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"[EXEC] Process started with PID: {process.pid}")
        
        stdout_lines = []
        stderr_lines = []
        
        def read_stdout():
            logger.info(f"[EXEC-STDOUT] Thread started")
            line_count = 0
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line_count += 1
                        logger.info(f"[EXEC-STDOUT] Line {line_count}: {line.strip()}")
                        stdout_lines.append(line)
                        
                        # Send immediately
                        send_websocket_log_sync(execution_id, "stdout", line)
                        
                logger.info(f"[EXEC-STDOUT] Thread finished, total lines: {line_count}")
            except Exception as e:
                logger.error(f"[EXEC-STDOUT] Error: {e}", exc_info=True)
            finally:
                process.stdout.close()
        
        def read_stderr():
            logger.info(f"[EXEC-STDERR] Thread started")
            try:
                for line in iter(process.stderr.readline, ''):
                    if line:
                        logger.info(f"[EXEC-STDERR] {line.strip()}")
                        stderr_lines.append(line)
                        send_websocket_log_sync(execution_id, "stderr", line)
                logger.info(f"[EXEC-STDERR] Thread finished")
            except Exception as e:
                logger.error(f"[EXEC-STDERR] Error: {e}", exc_info=True)
            finally:
                process.stderr.close()
        
        # Start reader threads
        stdout_thread = threading.Thread(target=read_stdout, daemon=False)
        stderr_thread = threading.Thread(target=read_stderr, daemon=False)
        
        stdout_thread.start()
        stderr_thread.start()
        
        logger.info(f"[EXEC] Waiting for process to complete...")
        
        # Wait for completion
        try:
            exit_code = process.wait(timeout=timeout)
            logger.info(f"[EXEC] Process exited with code: {exit_code}")
        except subprocess.TimeoutExpired:
            logger.warning(f"[EXEC] Process timed out after {timeout}s")
            process.kill()
            exit_code = -1
        
        # Wait for threads
        logger.info(f"[EXEC] Waiting for reader threads...")
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        logger.info(f"[EXEC] Collected {len(stdout_lines)} stdout lines, {len(stderr_lines)} stderr lines")
        
        stdout = ''.join(stdout_lines)
        stderr = ''.join(stderr_lines)
        
        return exit_code, stdout, stderr
        
    except Exception as e:
        logger.error(f"[EXEC] Error: {e}", exc_info=True)
        send_websocket_log_sync(execution_id, "error", f"Execution error: {str(e)}\n")
        return 1, "", str(e)
    
    finally:
        try:
            os.unlink(script_path)
            logger.info(f"[EXEC] Cleaned up temp file")
        except Exception as e:
            logger.warning(f"[EXEC] Failed to cleanup: {e}")


@celery_app.task
def cleanup_old_containers():
    """Periodic task to cleanup old Docker containers"""
    try:
        from app.core.docker_executor import DockerExecutor
        executor = DockerExecutor()
        count = executor.cleanup_old_containers(max_age_hours=24)
        return f"Cleaned up {count} old containers"
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return f"Cleanup failed: {str(e)}"