import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base_class import Base
from app.db.session import get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_create_script():
    """Test creating a new script"""
    script_data = {
        "name": "test-script",
        "description": "A test script",
        "script_type": "bash",
        "content": "echo 'Hello World'",
        "version": "1.0.0"
    }
    response = client.post("/api/v1/scripts/", json=script_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == script_data["name"]
    assert data["status"] == "draft"
    assert "id" in data


def test_list_scripts():
    """Test listing all scripts"""
    # Create a script first
    script_data = {
        "name": "list-test-script",
        "description": "Test script for listing",
        "script_type": "python",
        "content": "print('test')",
        "version": "1.0.0"
    }
    client.post("/api/v1/scripts/", json=script_data)
    
    # List scripts
    response = client.get("/api/v1/scripts/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_script():
    """Test getting a specific script"""
    # Create a script
    script_data = {
        "name": "get-test-script",
        "description": "Test script for retrieval",
        "script_type": "bash",
        "content": "ls -la",
        "version": "1.0.0"
    }
    create_response = client.post("/api/v1/scripts/", json=script_data)
    script_id = create_response.json()["id"]
    
    # Get the script
    response = client.get(f"/api/v1/scripts/{script_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == script_id
    assert data["name"] == script_data["name"]


def test_update_script():
    """Test updating a script"""
    # Create a script
    script_data = {
        "name": "update-test-script",
        "description": "Original description",
        "script_type": "bash",
        "content": "echo 'original'",
        "version": "1.0.0"
    }
    create_response = client.post("/api/v1/scripts/", json=script_data)
    script_id = create_response.json()["id"]
    
    # Update the script
    update_data = {
        "description": "Updated description",
        "version": "1.1.0"
    }
    response = client.put(f"/api/v1/scripts/{script_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == update_data["description"]
    assert data["version"] == update_data["version"]


def test_delete_script():
    """Test deleting a script"""
    # Create a script
    script_data = {
        "name": "delete-test-script",
        "description": "Script to be deleted",
        "script_type": "bash",
        "content": "echo 'delete me'",
        "version": "1.0.0"
    }
    create_response = client.post("/api/v1/scripts/", json=script_data)
    script_id = create_response.json()["id"]
    
    # Delete the script
    response = client.delete(f"/api/v1/scripts/{script_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/scripts/{script_id}")
    assert get_response.status_code == 404


def test_create_duplicate_script():
    """Test that creating duplicate scripts fails"""
    script_data = {
        "name": "duplicate-script",
        "description": "Test duplicate",
        "script_type": "bash",
        "content": "echo 'test'",
        "version": "1.0.0"
    }
    # Create first script
    response1 = client.post("/api/v1/scripts/", json=script_data)
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post("/api/v1/scripts/", json=script_data)
    assert response2.status_code == 400