import os
from celery import Celery
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.script import Script
from app.models.execution import ExecutionStatus, Execution
from app.core.docker_executor import DockerExecutor
from app.services.SecretService import SecretService
from datetime import datetime, timezone

celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)


@celery_app.task
def execute_script_task(execution_id: int):
    """Celery task to execute a script based on the execution ID with secret injection.
    
    Args:
        execution_id (int): The ID of the execution record.
    """
    db = SessionLocal()
    executor = DockerExecutor()
    
    try:
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return
        
        script = db.query(Script).filter(Script.id == execution.script_id).first()
        if not script:
            execution.status = ExecutionStatus.FAILED
            execution.error = "Script not found"
            db.commit()
            return
        
        # Update status to running
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Get secrets for this script
        secrets_dict = SecretService.get_secrets_for_script(
            db=db,
            script_id=script.id,
            execution_id=execution.id,
            user_id=None,  # System execution
            username=execution.executed_by
        )
        
        # Prepare environment variables from execution parameters
        env_vars = {}
        if execution.parameters:
            for key, value in execution.parameters.items():
                # Convert to string for environment variables
                env_vars[key] = str(value) if not isinstance(value, str) else value
        env_vars.update(secrets_dict)  # Inject secrets as env vars
        
        # Execute script in Docker container
        try:
            exit_code, stdout, stderr = executor.execute(
                script_type=script.script_type,
                script_content=script.content,
                env_vars=env_vars,
                timeout=300  # 5 minutes default
            )
            
            execution.output = stdout
            execution.error = stderr if exit_code != 0 else None
            execution.status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Execution error: {str(e)}"
            execution.output = None
        
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()
        
    except Exception as e:
        # Log the error
        print(f"Task execution error: {str(e)}")
        if execution:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Task error: {str(e)}"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
        
    finally:
        db.close()

@celery_app.task
def cleanup_old_containers():
    """
    Periodic task to cleanup old Docker containers
    """
    executor = DockerExecutor()
    count = executor.cleanup_old_containers(max_age_hours=24)
    return f"Cleaned up {count} old containers"

def execute_locally(script_content: str, script_type: str, env_vars: dict):
    """Execute script locally with environment variables"""
    import subprocess
    import tempfile
    
    # Create temporary script file
    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{script_type}', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        # Execute with environment variables containing secrets
        if script_type == 'bash':
            result = subprocess.run(
                ['bash', script_path],
                capture_output=True,
                text=True,
                timeout=300,
                env=env_vars  # Secrets injected here!
            )
        elif script_type == 'python':
            result = subprocess.run(
                ['python3', script_path],
                capture_output=True,
                text=True,
                timeout=300,
                env=env_vars  # Secrets injected here!
            )
        # Add other script types...
        
        return {
            'output': result.stdout,
            'error': result.stderr,
            'exit_code': result.returncode
        }
    
    finally:
        # Clean up
        os.unlink(script_path)