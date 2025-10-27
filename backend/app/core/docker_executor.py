import docker
import tempfile
import os
from typing import Dict, Tuple, Optional
from app.models.script import ScriptType


class DockerExecutor:
    """Secure script executor using Docker containers"""
    
    # Container configurations for different script types
    CONTAINER_CONFIGS = {
        ScriptType.BASH: {
            "image": "alpine:latest",
            "command_prefix": ["sh", "-c"],
            "memory_limit": "512m",
            "cpu_quota": 50000,  # 0.5 CPU
        },
        ScriptType.PYTHON: {
            "image": "python:3.11-alpine",
            "command_prefix": ["python", "-c"],
            "memory_limit": "512m",
            "cpu_quota": 50000,
        },
        ScriptType.ANSIBLE: {
            "image": "ansible/ansible:latest",
            "command_prefix": ["ansible-playbook"],
            "memory_limit": "1g",
            "cpu_quota": 100000,  # 1 CPU
        },
        ScriptType.TERRAFORM: {
            "image": "hashicorp/terraform:latest",
            "command_prefix": ["terraform"],
            "memory_limit": "1g",
            "cpu_quota": 100000,
        }
    }
    
    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            # Verify Docker is accessible
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")
    
    def pull_image_if_needed(self, image: str) -> None:
        """Pull Docker image if not present"""
        try:
            self.client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"Pulling image {image}...")
            self.client.images.pull(image)
    
    def execute_bash(self, script_content: str, env_vars: Optional[Dict[str, str]] = None, 
                     timeout: int = 300) -> Tuple[int, str, str]:
        """Execute bash script in isolated container"""
        config = self.CONTAINER_CONFIGS[ScriptType.BASH]
        self.pull_image_if_needed(config["image"])
        
        try:
            container = self.client.containers.run(
                image=config["image"],
                command=config["command_prefix"] + [script_content],
                environment=env_vars or {},
                network_disabled=True,  # No network access
                mem_limit=config["memory_limit"],
                cpu_quota=config["cpu_quota"],
                detach=True,
                remove=False,  # Keep for log retrieval
                security_opt=["no-new-privileges"],
                read_only=True,  # Read-only filesystem
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'}  # Temporary writable space
            )
            
            # Wait for completion with timeout
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            # Cleanup
            container.remove(force=True)
            
            return exit_code, stdout, stderr
            
        except docker.errors.ContainerError as e:
            return 1, "", str(e)
        except Exception as e:
            return 1, "", f"Execution error: {str(e)}"
    
    def execute_python(self, script_content: str, env_vars: Optional[Dict[str, str]] = None,
                       timeout: int = 300) -> Tuple[int, str, str]:
        """Execute Python script in isolated container"""
        config = self.CONTAINER_CONFIGS[ScriptType.PYTHON]
        self.pull_image_if_needed(config["image"])
        
        try:
            container = self.client.containers.run(
                image=config["image"],
                command=config["command_prefix"] + [script_content],
                environment=env_vars or {},
                network_disabled=True,
                mem_limit=config["memory_limit"],
                cpu_quota=config["cpu_quota"],
                detach=True,
                remove=False,
                security_opt=["no-new-privileges"],
                read_only=True,
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'}
            )
            
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            container.remove(force=True)
            
            return exit_code, stdout, stderr
            
        except docker.errors.ContainerError as e:
            return 1, "", str(e)
        except Exception as e:
            return 1, "", f"Execution error: {str(e)}"
    
    def execute_ansible(self, script_content: str, env_vars: Optional[Dict[str, str]] = None,
                        timeout: int = 600) -> Tuple[int, str, str]:
        """Execute Ansible playbook in isolated container"""
        config = self.CONTAINER_CONFIGS[ScriptType.ANSIBLE]
        self.pull_image_if_needed(config["image"])
        
        # Create temporary playbook file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(script_content)
            playbook_path = f.name
        
        try:
            # Mount playbook as volume
            volumes = {
                playbook_path: {'bind': '/playbook.yml', 'mode': 'ro'}
            }
            
            container = self.client.containers.run(
                image=config["image"],
                command=[*config["command_prefix"], '/playbook.yml'],
                environment=env_vars or {},
                network_disabled=False,  # Ansible may need network
                mem_limit=config["memory_limit"],
                cpu_quota=config["cpu_quota"],
                volumes=volumes,
                detach=True,
                remove=False,
                security_opt=["no-new-privileges"]
            )
            
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            container.remove(force=True)
            
            return exit_code, stdout, stderr
            
        except docker.errors.ContainerError as e:
            return 1, "", str(e)
        except Exception as e:
            return 1, "", f"Execution error: {str(e)}"
        finally:
            # Cleanup temp file
            if os.path.exists(playbook_path):
                os.unlink(playbook_path)
    
    def execute_terraform(self, script_content: str, env_vars: Optional[Dict[str, str]] = None,
                          timeout: int = 600) -> Tuple[int, str, str]:
        """Execute Terraform in isolated container"""
        config = self.CONTAINER_CONFIGS[ScriptType.TERRAFORM]
        self.pull_image_if_needed(config["image"])
        
        # Create temporary directory for Terraform files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write main.tf
            tf_file = os.path.join(tmpdir, 'main.tf')
            with open(tf_file, 'w') as f:
                f.write(script_content)
            
            try:
                # Mount workspace as volume
                volumes = {
                    tmpdir: {'bind': '/workspace', 'mode': 'rw'}
                }
                
                # First, run terraform init
                init_container = self.client.containers.run(
                    image=config["image"],
                    command=['init'],
                    environment=env_vars or {},
                    mem_limit=config["memory_limit"],
                    cpu_quota=config["cpu_quota"],
                    volumes=volumes,
                    working_dir='/workspace',
                    detach=True,
                    remove=False
                )
                
                init_result = init_container.wait(timeout=120)
                init_logs = init_container.logs().decode('utf-8')
                init_container.remove(force=True)
                
                if init_result['StatusCode'] != 0:
                    return 1, init_logs, "Terraform init failed"
                
                # Then run terraform plan (or apply based on content)
                plan_container = self.client.containers.run(
                    image=config["image"],
                    command=['plan'],
                    environment=env_vars or {},
                    mem_limit=config["memory_limit"],
                    cpu_quota=config["cpu_quota"],
                    volumes=volumes,
                    working_dir='/workspace',
                    detach=True,
                    remove=False
                )
                
                plan_result = plan_container.wait(timeout=timeout)
                exit_code = plan_result['StatusCode']
                
                stdout = plan_container.logs(stdout=True, stderr=False).decode('utf-8')
                stderr = plan_container.logs(stdout=False, stderr=True).decode('utf-8')
                
                plan_container.remove(force=True)
                
                # Prepend init logs to output
                stdout = f"=== Terraform Init ===\n{init_logs}\n\n=== Terraform Plan ===\n{stdout}"
                
                return exit_code, stdout, stderr
                
            except docker.errors.ContainerError as e:
                return 1, "", str(e)
            except Exception as e:
                return 1, "", f"Execution error: {str(e)}"
    
    def execute(self, script_type: ScriptType, script_content: str, 
                env_vars: Optional[Dict[str, str]] = None, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute script based on type"""
        executors = {
            ScriptType.BASH: self.execute_bash,
            ScriptType.PYTHON: self.execute_python,
            ScriptType.ANSIBLE: self.execute_ansible,
            ScriptType.TERRAFORM: self.execute_terraform,
        }
        
        executor = executors.get(script_type)
        if not executor:
            return 1, "", f"Unsupported script type: {script_type}"
        
        return executor(script_content, env_vars, timeout)
    
    def cleanup_old_containers(self, max_age_hours: int = 24) -> int:
        """Clean up old containers (maintenance function)"""
        count = 0
        for container in self.client.containers.list(all=True):
            # Remove containers older than max_age_hours
            created_at = container.attrs['Created']
            # Add cleanup logic here based on timestamp
            count += 1
        return count