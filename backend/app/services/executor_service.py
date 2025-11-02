"""
Fixed Unified Script Executor Service
File: backend/app/services/executor_service.py
"""

import docker
import tempfile
import os
import shutil
import logging
from typing import Tuple, Optional, Callable, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.script import ScriptType

logger = logging.getLogger(__name__)


@dataclass
class ExecutorConfig:
    """Configuration for Docker container execution"""
    image: str
    command_prefix: list
    memory_limit: str
    nano_cpus: int
    network_disabled: bool = True
    read_only: bool = True
    timeout: int = 300


class ExecutionStrategy(ABC):
    """Base strategy for script execution"""
    
    def __init__(self, docker_client: docker.DockerClient, config: ExecutorConfig):
        self.client = docker_client
        self.config = config
    
    @abstractmethod
    def execute(
        self, 
        content: str, 
        env_vars: Dict[str, str],
        timeout: int,
        log_callback: Optional[Callable[[str, str], None]]
    ) -> Tuple[int, str, str]:
        """Execute script and return (exit_code, stdout, stderr)"""
        pass
    
    def _pull_image_if_needed(self):
        """Pull Docker image if not present"""
        try:
            self.client.images.get(self.config.image)
            logger.debug(f"Image {self.config.image} already present")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image {self.config.image}...")
            self.client.images.pull(self.config.image)
            logger.info(f"Image {self.config.image} pulled successfully")
    
    def _stream_logs(
        self, 
        container, 
        log_callback: Optional[Callable[[str, str], None]]
    ) -> Tuple[str, str]:
        """Stream logs from container in real-time"""
        stdout_lines = []
        stderr_lines = []
        
        try:
            for log_chunk in container.logs(
                stream=True, 
                follow=True, 
                stdout=True, 
                stderr=True
            ):
                line = log_chunk.decode('utf-8', errors='replace')
                
                is_error = any(
                    word in line.lower() 
                    for word in ['error', 'fail', 'exception', 'traceback', 'fatal']
                )
                
                if is_error:
                    stderr_lines.append(line)
                    if log_callback:
                        log_callback("stderr", line)
                else:
                    stdout_lines.append(line)
                    if log_callback:
                        log_callback("stdout", line)
                
                logger.debug(f"Container log: {line.strip()}")
                
        except Exception as e:
            logger.error(f"Error streaming container logs: {e}")
            error_msg = f"Log streaming error: {str(e)}\n"
            stderr_lines.append(error_msg)
            if log_callback:
                log_callback("stderr", error_msg)
        
        return ''.join(stdout_lines), ''.join(stderr_lines)


class BashExecutor(ExecutionStrategy):
    """Execute bash scripts in Alpine Linux container"""
    
    def __init__(self, docker_client: docker.DockerClient):
        config = ExecutorConfig(
            image="alpine:latest",
            command_prefix=["sh", "-c"],
            memory_limit="512m",
            nano_cpus=500_000_000,
            network_disabled=True,
            read_only=True
        )
        super().__init__(docker_client, config)
    
    def execute(
        self, 
        content: str, 
        env_vars: Dict[str, str],
        timeout: int,
        log_callback: Optional[Callable[[str, str], None]]
    ) -> Tuple[int, str, str]:
        """Execute bash script"""
        self._pull_image_if_needed()
        
        container = None
        try:
            # FIX: Remove 'remove' parameter from create()
            container = self.client.containers.create(
                image=self.config.image,
                command=self.config.command_prefix + [content],
                environment=env_vars,
                detach=True,
                mem_limit=self.config.memory_limit,
                nano_cpus=self.config.nano_cpus,
                network_disabled=self.config.network_disabled,
                read_only=self.config.read_only,
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'},
                security_opt=["no-new-privileges"]
                # DON'T use 'remove' here - it's for run(), not create()
            )
            
            container.start()
            logger.info(f"[BASH] Container {container.id[:12]} started")
            
            stdout, stderr = self._stream_logs(container, log_callback)
            
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            logger.info(f"[BASH] Container exited with code {exit_code}")
            
            return exit_code, stdout, stderr
            
        except docker.errors.ContainerError as e:
            logger.error(f"[BASH] Container error: {e}")
            return 1, "", str(e)
        except Exception as e:
            logger.error(f"[BASH] Execution error: {e}", exc_info=True)
            return 1, "", f"Execution error: {str(e)}"
        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")


class PythonExecutor(ExecutionStrategy):
    """Execute Python scripts in Python container"""
    
    def __init__(self, docker_client: docker.DockerClient):
        config = ExecutorConfig(
            image="python:3.11-alpine",
            command_prefix=["python", "-c"],
            memory_limit="512m",
            nano_cpus=500_000_000
        )
        super().__init__(docker_client, config)
    
    def execute(
        self, 
        content: str, 
        env_vars: Dict[str, str],
        timeout: int,
        log_callback: Optional[Callable[[str, str], None]]
    ) -> Tuple[int, str, str]:
        """Execute Python script"""
        self._pull_image_if_needed()
        
        temp_dir = tempfile.mkdtemp()
        script_path = os.path.join(temp_dir, 'script.py')
        container = None
        
        try:
            with open(script_path, 'w') as f:
                f.write(content)
            
            container = self.client.containers.create(
                image=self.config.image,
                command=['python', '/app/script.py'],
                environment=env_vars,
                volumes={temp_dir: {'bind': '/app', 'mode': 'ro'}},
                detach=True,
                mem_limit=self.config.memory_limit,
                nano_cpus=self.config.nano_cpus,
                network_disabled=False,
                read_only=True,
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'},
                security_opt=["no-new-privileges"]
            )
            
            container.start()
            logger.info(f"[PYTHON] Container {container.id[:12]} started")
            
            stdout, stderr = self._stream_logs(container, log_callback)
            
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            logger.info(f"[PYTHON] Container exited with code {exit_code}")
            
            return exit_code, stdout, stderr
            
        except Exception as e:
            logger.error(f"[PYTHON] Execution error: {e}", exc_info=True)
            return 1, "", f"Execution error: {str(e)}"
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)


class AnsibleExecutor(ExecutionStrategy):
    """Execute Ansible playbooks"""
    
    def __init__(self, docker_client: docker.DockerClient):
        config = ExecutorConfig(
            image="ansible/ansible:latest",
            command_prefix=["ansible-playbook"],
            memory_limit="1g",
            nano_cpus=1_000_000_000,
            network_disabled=False,
            read_only=False
        )
        super().__init__(docker_client, config)
    
    def execute(
        self, 
        content: str, 
        env_vars: Dict[str, str],
        timeout: int,
        log_callback: Optional[Callable[[str, str], None]]
    ) -> Tuple[int, str, str]:
        """Execute Ansible playbook"""
        self._pull_image_if_needed()
        
        temp_dir = tempfile.mkdtemp()
        playbook_path = os.path.join(temp_dir, 'playbook.yml')
        container = None
        
        try:
            with open(playbook_path, 'w') as f:
                f.write(content)
            
            container = self.client.containers.create(
                image=self.config.image,
                command=['ansible-playbook', '/ansible/playbook.yml', '-v'],
                environment=env_vars,
                volumes={temp_dir: {'bind': '/ansible', 'mode': 'ro'}},
                detach=True,
                mem_limit=self.config.memory_limit,
                nano_cpus=self.config.nano_cpus,
                network_disabled=self.config.network_disabled,
                security_opt=["no-new-privileges"]
            )
            
            container.start()
            logger.info(f"[ANSIBLE] Container {container.id[:12]} started")
            
            stdout, stderr = self._stream_logs(container, log_callback)
            
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            logger.info(f"[ANSIBLE] Container exited with code {exit_code}")
            
            return exit_code, stdout, stderr
            
        except Exception as e:
            logger.error(f"[ANSIBLE] Execution error: {e}", exc_info=True)
            return 1, "", f"Execution error: {str(e)}"
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)


class TerraformExecutor(ExecutionStrategy):
    """Execute Terraform configurations"""
    
    def __init__(self, docker_client: docker.DockerClient):
        config = ExecutorConfig(
            image="hashicorp/terraform:latest",
            command_prefix=["terraform"],
            memory_limit="1g",
            nano_cpus=1_000_000_000,
            network_disabled=False,
            read_only=False
        )
        super().__init__(docker_client, config)
    
    def execute(
        self, 
        content: str, 
        env_vars: Dict[str, str],
        timeout: int,
        log_callback: Optional[Callable[[str, str], None]]
    ) -> Tuple[int, str, str]:
        """Execute Terraform init + plan"""
        self._pull_image_if_needed()
        
        temp_dir = tempfile.mkdtemp()
        tf_path = os.path.join(temp_dir, 'main.tf')
        
        try:
            with open(tf_path, 'w') as f:
                f.write(content)
            
            all_stdout = []
            all_stderr = []
            
            # Step 1: terraform init
            if log_callback:
                log_callback("info", "\n🔧 Running terraform init...\n")
            
            init_container = None
            try:
                init_container = self.client.containers.create(
                    image=self.config.image,
                    command=['init'],
                    environment=env_vars,
                    volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},
                    working_dir='/workspace',
                    detach=True,
                    mem_limit=self.config.memory_limit,
                    nano_cpus=self.config.nano_cpus
                )
                
                init_container.start()
                logger.info(f"[TERRAFORM] Init container {init_container.id[:12]} started")
                
                init_stdout, init_stderr = self._stream_logs(init_container, log_callback)
                all_stdout.append(init_stdout)
                all_stderr.append(init_stderr)
                
                init_result = init_container.wait(timeout=120)
                
                if init_result['StatusCode'] != 0:
                    if log_callback:
                        log_callback("error", "\n❌ Terraform init failed\n")
                    return init_result['StatusCode'], ''.join(all_stdout), ''.join(all_stderr)
                
                if log_callback:
                    log_callback("info", "\n✅ Terraform init completed\n")
            finally:
                if init_container:
                    try:
                        init_container.remove(force=True)
                    except Exception as e:
                        logger.warning(f"Failed to remove init container: {e}")
            
            # Step 2: terraform plan
            if log_callback:
                log_callback("info", "\n📋 Running terraform plan...\n")
            
            plan_container = None
            try:
                plan_container = self.client.containers.create(
                    image=self.config.image,
                    command=['plan'],
                    environment=env_vars,
                    volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},
                    working_dir='/workspace',
                    detach=True,
                    mem_limit=self.config.memory_limit,
                    nano_cpus=self.config.nano_cpus
                )
                
                plan_container.start()
                logger.info(f"[TERRAFORM] Plan container {plan_container.id[:12]} started")
                
                plan_stdout, plan_stderr = self._stream_logs(plan_container, log_callback)
                all_stdout.append(plan_stdout)
                all_stderr.append(plan_stderr)
                
                plan_result = plan_container.wait(timeout=timeout)
                
                if plan_result['StatusCode'] == 0 and log_callback:
                    log_callback("info", "\n✅ Terraform plan completed\n")
                
                return plan_result['StatusCode'], ''.join(all_stdout), ''.join(all_stderr)
            finally:
                if plan_container:
                    try:
                        plan_container.remove(force=True)
                    except Exception as e:
                        logger.warning(f"Failed to remove plan container: {e}")
            
        except Exception as e:
            logger.error(f"[TERRAFORM] Execution error: {e}", exc_info=True)
            return 1, "", f"Execution error: {str(e)}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class ExecutorService:
    """
    Unified executor service using strategy pattern
    """
    
    def __init__(self):
        """Initialize executor service and Docker client"""
        self.docker_client = None
        self._init_docker_client()
        
        # Executor strategies for each script type
        self._executors = {
            ScriptType.BASH: BashExecutor,
            ScriptType.PYTHON: PythonExecutor,
            ScriptType.ANSIBLE: AnsibleExecutor,
            ScriptType.TERRAFORM: TerraformExecutor,
        }
    
    def _init_docker_client(self):
        """Initialize Docker client with error handling"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("[EXECUTOR] Docker connected successfully")
        except docker.errors.DockerException as e:
            logger.error(f"[EXECUTOR] Docker connection failed: {e}")
            self.docker_client = None
        except Exception as e:
            logger.error(f"[EXECUTOR] Unexpected error connecting to Docker: {e}")
            self.docker_client = None
    
    def execute(
        self,
        script_type: ScriptType,
        content: str,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: int = 300,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> Tuple[int, str, str]:
        """Execute script with appropriate executor"""
        if not self.docker_client:
            error_msg = "Docker is not available"
            logger.error(f"[EXECUTOR] {error_msg}")
            return 1, "", error_msg
        
        executor_class = self._executors.get(script_type)
        if not executor_class:
            error_msg = f"Unsupported script type: {script_type}"
            logger.error(f"[EXECUTOR] {error_msg}")
            return 1, "", error_msg
        
        try:
            executor = executor_class(self.docker_client)
            return executor.execute(
                content=content,
                env_vars=env_vars or {},
                timeout=timeout,
                log_callback=log_callback
            )
        except Exception as e:
            logger.error(f"[EXECUTOR] Fatal error during execution: {e}", exc_info=True)
            return 1, "", f"Fatal execution error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Docker is available"""
        return self.docker_client is not None


# Global executor service instance
executor_service = ExecutorService()