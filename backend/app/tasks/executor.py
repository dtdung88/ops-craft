"""
Celery executor with Docker sandboxing and Redis streaming for ALL script types
File: backend/app/tasks/executor.py
"""
import os
import docker
import tempfile
import threading
import logging
import shutil
from celery import Celery
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.script import Script, ScriptType
from app.models.execution import ExecutionStatus, Execution
from app.services.SecretService import SecretService
from app.core.websocket_bridge import websocket_bridge

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

# Docker client
try:
    docker_client = docker.from_env()
    docker_client.ping()
    logger.info("[DOCKER] Connected successfully")
except Exception as e:
    logger.error(f"[DOCKER] Failed to connect: {e}")
    docker_client = None


def send_log(execution_id: int, log_type: str, content: str):
    """Send log via Redis"""
    try:
        websocket_bridge.publish_log(execution_id, log_type, content)
    except Exception as e:
        logger.error(f"[REDIS-LOG] Error: {e}")


def send_status(execution_id: int, status: str, metadata: dict = None):
    """Send status via Redis"""
    try:
        websocket_bridge.publish_status(execution_id, status, metadata)
    except Exception as e:
        logger.error(f"[REDIS-STATUS] Error: {e}")


@celery_app.task
def execute_script_task(execution_id: int):
    """Execute script with Docker sandboxing and real-time streaming"""
    
    logger.info(f"[TASK] Starting execution {execution_id}")
    
    db = SessionLocal()
    
    try:
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error(f"[TASK] Execution {execution_id} not found")
            return
        
        script = db.query(Script).filter(Script.id == execution.script_id).first()
        if not script:
            execution.status = ExecutionStatus.FAILED
            execution.error = "Script not found"
            db.commit()
            return
        
        logger.info(f"[TASK] Executing: {script.name} (type: {script.script_type})")
        
        # Update to running
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Send initial messages
        send_status(execution.id, "running", {"started_at": execution.started_at.isoformat()})
        send_log(execution.id, "info", f"🚀 Starting: {script.name}\n")
        send_log(execution.id, "info", f"📝 Type: {script.script_type}\n")
        
        # Get secrets
        secrets_dict = SecretService.get_secrets_for_script(
            db=db,
            script_id=script.id,
            execution_id=execution.id,
            user_id=None,
            username=execution.executed_by
        )
        
        if secrets_dict:
            send_log(execution.id, "info", f"🔐 Injected {len(secrets_dict)} secret(s)\n")
        
        # Prepare environment
        env_vars = {}
        if execution.parameters:
            for key, value in execution.parameters.items():
                env_vars[key] = str(value) if not isinstance(value, str) else value
        env_vars.update(secrets_dict or {})
        
        # Execute based on script type
        try:
            send_log(execution.id, "info", f"⚙️  Executing {script.script_type} script in Docker...\n")
            send_log(execution.id, "info", "─" * 50 + "\n")
            
            # Route to appropriate executor
            if script.script_type == ScriptType.BASH:
                exit_code, stdout, stderr = execute_bash_docker(
                    script.content, env_vars, execution.id
                )
            elif script.script_type == ScriptType.PYTHON:
                exit_code, stdout, stderr = execute_python_docker(
                    script.content, env_vars, execution.id
                )
            elif script.script_type == ScriptType.ANSIBLE:
                exit_code, stdout, stderr = execute_ansible_docker(
                    script.content, env_vars, execution.id
                )
            elif script.script_type == ScriptType.TERRAFORM:
                exit_code, stdout, stderr = execute_terraform_docker(
                    script.content, env_vars, execution.id
                )
            else:
                send_log(execution.id, "error", f"❌ Unsupported script type: {script.script_type}\n")
                exit_code = 1
                stdout = ""
                stderr = f"Unsupported script type: {script.script_type}"
            
            send_log(execution.id, "info", "\n" + "─" * 50 + "\n")
            
            execution.output = stdout
            execution.error = stderr if exit_code != 0 else None
            execution.status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
            
            if exit_code == 0:
                send_log(execution.id, "info", "✅ Completed successfully\n")
            else:
                send_log(execution.id, "error", f"❌ Failed (exit code: {exit_code})\n")
            
        except Exception as e:
            logger.error(f"[TASK] Error: {e}", exc_info=True)
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            send_log(execution.id, "error", f"❌ Error: {str(e)}\n")
        
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        send_status(execution.id, execution.status.value, {
            "completed_at": execution.completed_at.isoformat()
        })
        
        logger.info(f"[TASK] Completed execution {execution_id}")
        
    except Exception as e:
        logger.error(f"[TASK] Fatal error: {e}", exc_info=True)
    finally:
        db.close()


def stream_docker_logs(container, execution_id: int):
    """Stream Docker container logs in real-time"""
    stdout_lines = []
    stderr_lines = []
    
    try:
        # Stream logs in real-time
        for log_chunk in container.logs(stream=True, follow=True, stdout=True, stderr=True):
            line = log_chunk.decode('utf-8', errors='replace')
            
            # Detect if it's an error (simple heuristic)
            is_error = any(word in line.lower() for word in ['error', 'fail', 'exception', 'traceback'])
            
            if is_error:
                stderr_lines.append(line)
                send_log(execution_id, "stderr", line)
            else:
                stdout_lines.append(line)
                send_log(execution_id, "stdout", line)
            
    except Exception as e:
        logger.error(f"[DOCKER-STREAM] Error: {e}")
    
    return ''.join(stdout_lines), ''.join(stderr_lines)


def execute_bash_docker(script_content: str, env_vars: dict, execution_id: int):
    """Execute bash script in Alpine Docker container with streaming"""
    
    if not docker_client:
        send_log(execution_id, "error", "❌ Docker not available\n")
        return 1, "", "Docker not available"
    
    try:
        send_log(execution_id, "info", "🐳 Starting Alpine container...\n")
        
        # Create and start container
        container = docker_client.containers.create(
            image='alpine:latest',
            command=['sh', '-c', script_content],
            environment=env_vars,
            detach=True,
            mem_limit='512m',
            nano_cpus=500000000,  # 0.5 CPU
            network_disabled=True,
            read_only=True,
            tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'}
        )
        
        container.start()
        logger.info(f"[BASH] Container {container.id[:12]} started")
        
        # Stream logs in real-time
        stdout, stderr = stream_docker_logs(container, execution_id)
        
        # Wait for completion
        result = container.wait(timeout=300)
        exit_code = result['StatusCode']
        
        # Cleanup
        container.remove(force=True)
        
        return exit_code, stdout, stderr
        
    except docker.errors.ImageNotFound:
        send_log(execution_id, "info", "📥 Pulling alpine:latest image...\n")
        docker_client.images.pull('alpine:latest')
        return execute_bash_docker(script_content, env_vars, execution_id)
    except Exception as e:
        logger.error(f"[BASH] Error: {e}")
        return 1, "", str(e)


def execute_python_docker(script_content: str, env_vars: dict, execution_id: int):
    """Execute Python script in Docker with auto dependency installation"""
    
    if not docker_client:
        send_log(execution_id, "error", "❌ Docker not available\n")
        return 1, "", "Docker not available"
    
    try:
        send_log(execution_id, "info", "🐳 Starting Python container...\n")
        
        # Detect if script has requirements
        has_imports = 'import ' in script_content or 'from ' in script_content
        
        # Create temporary directory for script
        temp_dir = tempfile.mkdtemp()
        script_path = os.path.join(temp_dir, 'script.py')
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Extract imports and create auto-install wrapper
        if has_imports:
            send_log(execution_id, "info", "📦 Auto-installing dependencies...\n")
            
            # Create wrapper that installs packages
            wrapper = f"""
import subprocess
import sys

# Try to import and install if missing
script_content = '''
{script_content}
'''

# Extract imports
import re
imports = re.findall(r'^(?:from|import)\\s+(\\w+)', script_content, re.MULTILINE)
packages = list(set(imports))

# Try to install missing packages
for package in packages:
    if package not in ['sys', 'os', 'time', 'datetime', 'json', 're', 'math', 'random']:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {{package}}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', package])

# Execute the actual script
exec(script_content)
"""
            with open(script_path, 'w') as f:
                f.write(wrapper)
        
        # Create and start container with volume mount
        container = docker_client.containers.create(
            image='python:3.11-alpine',
            command=['python', '/app/script.py'],
            environment=env_vars,
            volumes={temp_dir: {'bind': '/app', 'mode': 'ro'}},
            detach=True,
            mem_limit='512m',
            nano_cpus=500000000
        )
        
        container.start()
        logger.info(f"[PYTHON] Container {container.id[:12]} started")
        
        # Stream logs
        stdout, stderr = stream_docker_logs(container, execution_id)
        
        # Wait for completion
        result = container.wait(timeout=300)
        exit_code = result['StatusCode']
        
        # Cleanup
        container.remove(force=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return exit_code, stdout, stderr
        
    except docker.errors.ImageNotFound:
        send_log(execution_id, "info", "📥 Pulling python:3.11-alpine image...\n")
        docker_client.images.pull('python:3.11-alpine')
        return execute_python_docker(script_content, env_vars, execution_id)
    except Exception as e:
        logger.error(f"[PYTHON] Error: {e}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 1, "", str(e)


def execute_ansible_docker(script_content: str, env_vars: dict, execution_id: int):
    """Execute Ansible playbook in Docker"""
    
    if not docker_client:
        send_log(execution_id, "error", "❌ Docker not available\n")
        return 1, "", "Docker not available"
    
    try:
        send_log(execution_id, "info", "🐳 Starting Ansible container...\n")
        
        # Create temp directory with playbook
        temp_dir = tempfile.mkdtemp()
        playbook_path = os.path.join(temp_dir, 'playbook.yml')
        
        with open(playbook_path, 'w') as f:
            f.write(script_content)
        
        # Create and start container
        container = docker_client.containers.create(
            image='ansible/ansible:latest',
            command=['ansible-playbook', '/ansible/playbook.yml', '-v'],
            environment=env_vars,
            volumes={temp_dir: {'bind': '/ansible', 'mode': 'ro'}},
            detach=True,
            mem_limit='1g',
            nano_cpus=1000000000  # 1 CPU
        )
        
        container.start()
        logger.info(f"[ANSIBLE] Container {container.id[:12]} started")
        
        # Stream logs
        stdout, stderr = stream_docker_logs(container, execution_id)
        
        # Wait for completion
        result = container.wait(timeout=600)
        exit_code = result['StatusCode']
        
        # Cleanup
        container.remove(force=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return exit_code, stdout, stderr
        
    except docker.errors.ImageNotFound:
        send_log(execution_id, "info", "📥 Pulling ansible/ansible:latest image...\n")
        docker_client.images.pull('ansible/ansible:latest')
        return execute_ansible_docker(script_content, env_vars, execution_id)
    except Exception as e:
        logger.error(f"[ANSIBLE] Error: {e}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 1, "", str(e)


def execute_terraform_docker(script_content: str, env_vars: dict, execution_id: int):
    """Execute Terraform in Docker"""
    
    if not docker_client:
        send_log(execution_id, "error", "❌ Docker not available\n")
        return 1, "", "Docker not available"
    
    try:
        send_log(execution_id, "info", "🐳 Starting Terraform container...\n")
        
        # Create temp directory with terraform files
        temp_dir = tempfile.mkdtemp()
        tf_path = os.path.join(temp_dir, 'main.tf')
        
        with open(tf_path, 'w') as f:
            f.write(script_content)
        
        all_stdout = []
        all_stderr = []
        
        # Step 1: terraform init
        send_log(execution_id, "info", "\n🔧 Running terraform init...\n")
        
        init_container = docker_client.containers.create(
            image='hashicorp/terraform:latest',
            command=['init'],
            environment=env_vars,
            volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},
            working_dir='/workspace',
            detach=True,
            mem_limit='1g'
        )
        
        init_container.start()
        
        # Stream init logs
        init_stdout, init_stderr = stream_docker_logs(init_container, execution_id)
        all_stdout.append(init_stdout)
        all_stderr.append(init_stderr)
        
        init_result = init_container.wait(timeout=120)
        init_container.remove(force=True)
        
        if init_result['StatusCode'] != 0:
            send_log(execution_id, "error", "\n❌ Terraform init failed\n")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return init_result['StatusCode'], ''.join(all_stdout), ''.join(all_stderr)
        
        send_log(execution_id, "info", "\n✅ Terraform init completed\n")
        
        # Step 2: terraform plan
        send_log(execution_id, "info", "\n📋 Running terraform plan...\n")
        
        plan_container = docker_client.containers.create(
            image='hashicorp/terraform:latest',
            command=['plan'],
            environment=env_vars,
            volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},
            working_dir='/workspace',
            detach=True,
            mem_limit='1g'
        )
        
        plan_container.start()
        
        # Stream plan logs
        plan_stdout, plan_stderr = stream_docker_logs(plan_container, execution_id)
        all_stdout.append(plan_stdout)
        all_stderr.append(plan_stderr)
        
        plan_result = plan_container.wait(timeout=600)
        plan_container.remove(force=True)
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if plan_result['StatusCode'] == 0:
            send_log(execution_id, "info", "\n✅ Terraform plan completed\n")
        
        return plan_result['StatusCode'], ''.join(all_stdout), ''.join(all_stderr)
        
    except docker.errors.ImageNotFound:
        send_log(execution_id, "info", "📥 Pulling hashicorp/terraform:latest image...\n")
        docker_client.images.pull('hashicorp/terraform:latest')
        return execute_terraform_docker(script_content, env_vars, execution_id)
    except Exception as e:
        logger.error(f"[TERRAFORM] Error: {e}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 1, "", str(e)


@celery_app.task
def cleanup_old_containers():
    """Cleanup old Docker containers"""
    if not docker_client:
        return "Docker not available"
    
    try:
        # Remove stopped containers
        containers = docker_client.containers.list(all=True, filters={'status': 'exited'})
        count = 0
        for container in containers:
            try:
                container.remove()
                count += 1
            except:
                pass
        return f"Cleaned up {count} containers"
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return f"Cleanup failed: {str(e)}"