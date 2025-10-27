import subprocess
import tempfile
import os
import re
from typing import Tuple, List
from app.models.script import ScriptType


class ScriptValidator:
    """Validator for different script types"""
    
    # Dangerous commands/patterns to check
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\s+/',  # rm -rf /
        r'\bdd\s+if=/dev/',  # dd operations
        r':()\{\s*:\|\:&\s*\};:',  # Fork bomb
        r'\bchmod\s+777',  # chmod 777
        r'\bcurl\s+.*\|\s*bash',  # Piping to bash
        r'\bwget\s+.*\|\s*sh',  # Piping to sh
        r'>/dev/sda',  # Writing to disk
    ]
    
    def __init__(self):
        """Initialize validator"""
        pass
    
    def _check_dangerous_patterns(self, content: str) -> List[str]:
        """Check for dangerous patterns in script"""
        found = []
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                found.append(pattern)
        return found
    
    def validate_bash(self, script_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate bash script using shellcheck
        Returns: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check for dangerous patterns
        dangerous_found = self._check_dangerous_patterns(script_content)
        if dangerous_found:
            errors.extend([f"Dangerous pattern detected: {p}" for p in dangerous_found])
        
        # Try shellcheck if available
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            
            result = subprocess.run(
                ['shellcheck', '-f', 'json', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Parse shellcheck output
                import json
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues:
                        level = issue.get('level', 'error')
                        message = f"Line {issue.get('line')}: {issue.get('message')}"
                        if level in ['error']:
                            errors.append(message)
                        else:
                            warnings.append(message)
                except json.JSONDecodeError:
                    warnings.append("Could not parse shellcheck output")
            
            os.unlink(temp_file)
            
        except FileNotFoundError:
            warnings.append("shellcheck not installed, skipping advanced validation")
        except Exception as e:
            warnings.append(f"Validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def validate_python(self, script_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate Python script using pylint and syntax check
        Returns: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check syntax first
        try:
            compile(script_content, '<string>', 'exec')
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return False, errors, warnings
        
        # Try pylint if available
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            
            result = subprocess.run(
                ['pylint', '--output-format=json', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse pylint output
            import json
            try:
                issues = json.loads(result.stdout)
                for issue in issues:
                    message = f"Line {issue.get('line')}: {issue.get('message')}"
                    if issue.get('type') in ['error', 'fatal']:
                        errors.append(message)
                    elif issue.get('type') in ['warning', 'convention', 'refactor']:
                        warnings.append(message)
            except json.JSONDecodeError:
                pass
            
            os.unlink(temp_file)
            
        except FileNotFoundError:
            warnings.append("pylint not installed, skipping advanced validation")
        except Exception as e:
            warnings.append(f"Validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def validate_ansible(self, script_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate Ansible playbook using ansible-lint
        Returns: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check YAML syntax
        try:
            import yaml
            yaml.safe_load(script_content)
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
            return False, errors, warnings
        
        # Try ansible-lint if available
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            
            result = subprocess.run(
                ['ansible-lint', '-f', 'json', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Parse ansible-lint output
                import json
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues:
                        message = f"Line {issue.get('line')}: {issue.get('message')}"
                        if issue.get('severity') in ['HIGH', 'MEDIUM']:
                            errors.append(message)
                        else:
                            warnings.append(message)
                except json.JSONDecodeError:
                    warnings.append("Could not parse ansible-lint output")
            
            os.unlink(temp_file)
            
        except FileNotFoundError:
            warnings.append("ansible-lint not installed, skipping advanced validation")
        except Exception as e:
            warnings.append(f"Validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def validate_terraform(self, script_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate Terraform configuration using terraform validate
        Returns: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Create temporary directory for terraform files
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tf_file = os.path.join(tmpdir, 'main.tf')
                with open(tf_file, 'w') as f:
                    f.write(script_content)
                
                # Run terraform init
                init_result = subprocess.run(
                    ['terraform', 'init', '-backend=false'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if init_result.returncode != 0:
                    errors.append(f"Terraform init failed: {init_result.stderr}")
                    return False, errors, warnings
                
                # Run terraform validate
                validate_result = subprocess.run(
                    ['terraform', 'validate', '-json'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Parse validation output
                import json
                try:
                    result = json.loads(validate_result.stdout)
                    if not result.get('valid', False):
                        for diag in result.get('diagnostics', []):
                            message = f"{diag.get('summary', '')}: {diag.get('detail', '')}"
                            if diag.get('severity') == 'error':
                                errors.append(message)
                            else:
                                warnings.append(message)
                except json.JSONDecodeError:
                    warnings.append("Could not parse terraform output")
                
        except FileNotFoundError:
            warnings.append("terraform not installed, skipping validation")
        except Exception as e:
            warnings.append(f"Validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def validate(self, script_type: ScriptType, script_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate script based on type
        Returns: (is_valid, errors, warnings)
        """
        validators = {
            ScriptType.BASH: self.validate_bash,
            ScriptType.PYTHON: self.validate_python,
            ScriptType.ANSIBLE: self.validate_ansible,
            ScriptType.TERRAFORM: self.validate_terraform,
        }
        
        validator = validators.get(script_type)
        if not validator:
            return False, [f"No validator for script type: {script_type}"], []
        
        return validator(script_content)


# Global validator instance
script_validator = ScriptValidator()