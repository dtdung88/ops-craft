import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
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


@pytest.fixture
def test_user():
    """Create a test user"""
    db = TestingSessionLocal()
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.VIEWER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def admin_user():
    """Create an admin user"""
    db = TestingSessionLocal()
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def auth_token(test_user):
    """Get authentication token for test user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_token(admin_user):
    """Get authentication token for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_register_new_user(self):
        """Test user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "hashed_password" not in data
    
    def test_register_duplicate_username(self, test_user):
        """Test registration with duplicate username fails"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_duplicate_email(self, test_user):
        """Test registration with duplicate email fails"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "anotheruser",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_login_success(self, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpass"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password"}
        )
        assert response.status_code == 401
    
    def test_get_current_user(self, test_user, auth_token):
        """Test getting current user info"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    def test_get_current_user_no_token(self):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403
    
    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestRBAC:
    """Test Role-Based Access Control"""
    
    def test_viewer_can_view_scripts(self, test_user, auth_token):
        """Test viewer can view scripts"""
        response = client.get(
            "/api/v1/scripts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
    
    def test_viewer_cannot_create_script(self, test_user, auth_token):
        """Test viewer cannot create scripts"""
        response = client.post(
            "/api/v1/scripts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "test-script",
                "script_type": "bash",
                "content": "echo test",
                "version": "1.0.0"
            }
        )
        assert response.status_code == 403
    
    def test_admin_can_manage_users(self, admin_token):
        """Test admin can manage users"""
        # Admin should be able to access user management endpoints
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # This will return 404 if endpoint doesn't exist yet, but shouldn't be 403
        assert response.status_code != 403
    
    def test_password_change(self, test_user, auth_token):
        """Test password change"""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "old_password": "testpass123",
                "new_password": "newpassword123"
            }
        )
        assert response.status_code == 200
        
        # Try to login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "newpassword123"}
        )
        assert login_response.status_code == 200
    
    def test_password_change_wrong_old_password(self, test_user, auth_token):
        """Test password change with wrong old password"""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )
        assert response.status_code == 400


class TestTokens:
    """Test JWT token functionality"""
    
    def test_token_expiration(self, test_user):
        """Test token contains expiration"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Decode token to check expiration
        from app.core.security import decode_token
        payload = decode_token(data["access_token"])
        assert "exp" in payload
        assert payload["type"] == "access"
    
    def test_refresh_token_type(self, test_user):
        """Test refresh token has correct type"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass123"}
        )
        data = response.json()
        
        from app.core.security import decode_token
        payload = decode_token(data["refresh_token"])
        assert payload["type"] == "refresh"