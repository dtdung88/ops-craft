import pytest
from app.models.script import ScriptType, ScriptStatus
from app.models.execution import ExecutionStatus


@pytest.mark.integration
class TestScriptExecutionFlow:
    """Integration tests for complete script execution flow"""
    
    def test_complete_execution_workflow(self, client, auth_headers, db):
        """Test complete workflow: create script -> execute -> check results"""
        
        # 1. Create script
        script_data = {
            "name": "test-integration-script",
            "description": "Integration test script",
            "script_type": "bash",
            "content": "echo 'Integration test'",
            "version": "1.0.0"
        }
        
        response = client.post(
            "/api/v1/scripts/",
            json=script_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        script = response.json()
        script_id = script["id"]
        
        # 2. Execute script
        execution_data = {
            "script_id": script_id,
            "parameters": {}
        }
        
        response = client.post(
            "/api/v1/executions",
            json=execution_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        execution = response.json()
        execution_id = execution["id"]
        
        # 3. Check execution status
        response = client.get(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        execution = response.json()
        assert execution["status"] in ["pending", "running", "success"]
        
        # 4. Cleanup
        response = client.delete(
            f"/api/v1/scripts/{script_id}",
            headers=auth_headers
        )
        assert response.status_code == 204