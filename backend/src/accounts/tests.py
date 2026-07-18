import pytest
from rest_framework.response import Response
from .utils import clear_auth_cookies, set_auth_cookies, remove_tokens

@pytest.fixture
def mock_auth_settings(settings):
    settings.AUTH_COOKIE = {
        "ACCESS_NAME": "access_token",
        "REFRESH_NAME": "refresh_token",
        "HTTP_ONLY": True,
        "SECURE": True,
        "SAMESITE": "Lax",
        "PATH": "/",
    }

    class MockLifetime:
        def total_seconds(self):
            return 3600
        
    class MockRefreshLifetime:
        def total_seconds(self):
            return 86400
        
    settings.SIMPLE_JWT = {
        "ACCESS_TOKEN_LIFETIME": MockLifetime(),
        "REFRESH_TOKEN_LIFETIME": MockRefreshLifetime(),
    }

def test_set_auth_cookies_both_tokens(mock_auth_settings):
    """ Khi truyền đầy đủ access token và refresh token """
    response = Response(data={"message": "Success"})
    access_token = "mock_access"
    refresh_token = "mock_refresh"

    set_auth_cookies(response, access_token, refresh_token)

    assert "access_token" in response.cookies
    access_cookie = response.cookies["access_token"]
    assert access_cookie.value == "mock_access_value"
    assert access_cookie["httponly"] is True
    assert access_cookie["secure"] is True
    assert access_cookie["samesite"] == "Lax"
    assert access_cookie["path"] == "/"
    assert access_cookie["max-age"] == 3600

    assert "refresh_token" in response.cookies
    refresh_cookie = response.cookies["refresh_token"]
    assert refresh_cookie.value == "mock_refresh_value"
    assert refresh_cookie["httponly"] is True
    assert refresh_cookie["secure"] is True
    assert refresh_cookie["samesite"] == "Lax"
    assert refresh_cookie["path"] == "/"
    assert refresh_cookie["max-age"] == 86400

def test_set_auth_cookies_only_access_token(mock_auth_settings):
    """ Khi chỉ truyền access token """
    response = Response(data={"message": "Success"})
    access_token = "mock_access_value"

    set_auth_cookies(response, access_token=access_token, refresh_token=None)

    assert "access_token" in response.cookies
    assert "refresh_token" not in response.cookies

def test_set_auth_cookies_only_refresh_token(mock_auth_settings):
    """ Khi chỉ truyền vào refresh token """
    response = Response(data={"message": "Success"})
    refresh_token = "mock_refresh_value"

    set_auth_cookies(response, access_token=None, refresh_token=refresh_token)

    assert "refresh_token" in response.cookies
    assert "access_token" not in response.cookies

def test_set_auth_cookies_no_tokens(mock_auth_settings):
    """ Khi không truyền vào token nào hết """
    response = Response(data={"message": "Success"})

    set_auth_cookies(response, access_token=None, refresh_token=None)

    assert len(response.cookies) == 0

def test_remove_tokens_both_present():
    """Test xóa sạch cả 2 token khi data có đủ cả 2"""
    initial_data = {"access": "mock_access", "refresh": "mock_refresh", "user_id": 123}
    response = Response(data=initial_data)

    remove_tokens(response)

    assert "access" not in response.data
    assert "refresh" not in response.data
    assert response.data["user_id"] == 123


def test_remove_tokens_only_access_present():
    """Test xóa access token khi data không có refresh token"""
    initial_data = {"access": "mock_access", "user_id": 123}
    response = Response(data=initial_data)

    remove_tokens(response)

    assert "access" not in response.data
    assert "refresh" not in response.data
    assert response.data["user_id"] == 123


def test_remove_tokens_only_refresh_present():
    """Test xóa refresh token khi data không có access token"""
    initial_data = {"refresh": "mock_refresh", "user_id": 123}
    response = Response(data=initial_data)

    remove_tokens(response)

    assert "access" not in response.data
    assert "refresh" not in response.data
    assert response.data["user_id"] == 123


def test_remove_tokens_none_present():
    """Test hoạt động bình thường khi data ban đầu trống/không chứa token nào"""
    initial_data = {"user_id": 123}
    response = Response(data=initial_data)

    remove_tokens(response)

    assert response.data == {"user_id": 123}

def test_clear_auth_cookies_having_both_tokens():
    """ Khi truyền vào cả 2 token để xóa """
    initial_data = {"access": "mock_access", "refresh": "mock_refresh"}
    response = Response(data=initial_data)

    clear_auth_cookies(response)

    assert len(response.cookies) == 0

def test_clear_auth_cookies_with_access_token():
    """Khi truyền vào access token để xóa"""
    initial_data = {"access": "mock_access"}
    response = Response(data=initial_data)

    clear_auth_cookies(response)

    assert len(response.cookies) == 0

def test_clear_auth_cookies_with_refresh_token():
    """Khi truyền vào refresh token để xóa"""
    initial_data = {"refresh": "mock_refresh"}
    response = Response(data=initial_data)

    clear_auth_cookies(response)

    assert len(response.cookies) == 0

def test_clear_auth_cookies_no_token():
    """Khi truyền vào refresh token để xóa"""
    response = Response(data={})

    clear_auth_cookies(response)

    assert len(response.cookies) == 0
