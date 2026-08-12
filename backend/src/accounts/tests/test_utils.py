from datetime import timedelta

import pytest
from rest_framework.response import Response

from accounts.utils import clear_auth_cookies, remove_tokens, set_auth_cookies


@pytest.mark.django_db
class TestAccountUtils:

    @pytest.fixture
    def mock_auth_settings(self, settings):
        settings.AUTH_COOKIE = {
            "ACCESS_NAME": "access_token",
            "REFRESH_NAME": "refresh_token",
            "HTTP_ONLY": True,
            "SECURE": True,
            "SAMESITE": "Lax",
            "PATH": "/",
        }

        settings.SIMPLE_JWT = {
            "ACCESS_TOKEN_LIFETIME": timedelta(seconds=3600),
            "REFRESH_TOKEN_LIFETIME": timedelta(seconds=86400),
        }

        return settings.AUTH_COOKIE

    def test_set_auth_cookies_both_tokens(self, mock_auth_settings):
        """Khi truyền đầy đủ access token và refresh token"""
        response = Response(data={"message": "Success"})
        access_token = "mock_access"
        refresh_token = "mock_refresh"

        set_auth_cookies(response, access_token, refresh_token)

        access_name = mock_auth_settings["ACCESS_NAME"]
        refresh_name = mock_auth_settings["REFRESH_NAME"]

        assert "access_token" in response.cookies
        access_cookie = response.cookies[access_name]
        assert access_cookie.value == "mock_access"
        assert access_cookie["httponly"] is True
        assert access_cookie["secure"] is True
        assert access_cookie["samesite"] == "Lax"
        assert access_cookie["path"] == "/"
        assert access_cookie["max-age"] == 3600

        assert "refresh_token" in response.cookies
        refresh_cookie = response.cookies[refresh_name]
        assert refresh_cookie.value == "mock_refresh"
        assert refresh_cookie["httponly"] is True
        assert refresh_cookie["secure"] is True
        assert refresh_cookie["samesite"] == "Lax"
        assert refresh_cookie["path"] == "/"
        assert refresh_cookie["max-age"] == 86400

    def test_set_auth_cookies_only_access_token(self, mock_auth_settings):
        """Khi chỉ truyền access token"""
        response = Response(data={"message": "Success"})
        access_token = "mock_access_value"

        set_auth_cookies(response, access_token=access_token, refresh_token=None)
        access_name = mock_auth_settings["ACCESS_NAME"]
        refresh_name = mock_auth_settings["REFRESH_NAME"]

        assert access_name in response.cookies
        assert refresh_name not in response.cookies

    def test_set_auth_cookies_only_refresh_token(self, mock_auth_settings):
        """Khi chỉ truyền vào refresh token"""
        response = Response(data={"message": "Success"})
        refresh_token = "mock_refresh_value"

        set_auth_cookies(response, access_token=None, refresh_token=refresh_token)

        access_name = mock_auth_settings["ACCESS_NAME"]
        refresh_name = mock_auth_settings["REFRESH_NAME"]

        assert refresh_name in response.cookies
        assert access_name not in response.cookies

    def test_set_auth_cookies_no_tokens(self, mock_auth_settings):
        """Khi không truyền vào token nào hết"""
        response = Response(data={"message": "Success"})

        set_auth_cookies(response, access_token=None, refresh_token=None)

        assert len(response.cookies) == 0

    def test_remove_tokens_both_present(self):
        """Test xóa sạch cả 2 token khi data có đủ cả 2"""
        initial_data = {
            "access": "mock_access",
            "refresh": "mock_refresh",
            "user_id": 123,
        }
        response = Response(data=initial_data)

        remove_tokens(response)

        assert "access" not in response.data
        assert "refresh" not in response.data
        assert response.data["user_id"] == 123

    def test_remove_tokens_only_access_present(self):
        """Test xóa access token khi data không có refresh token"""
        initial_data = {"access": "mock_access", "user_id": 123}
        response = Response(data=initial_data)

        remove_tokens(response)

        assert "access" not in response.data
        assert "refresh" not in response.data
        assert response.data["user_id"] == 123

    def test_remove_tokens_only_refresh_present(self):
        """Test xóa refresh token khi data không có access token"""
        initial_data = {"refresh": "mock_refresh", "user_id": 123}
        response = Response(data=initial_data)

        remove_tokens(response)

        assert "access" not in response.data
        assert "refresh" not in response.data
        assert response.data["user_id"] == 123

    def test_remove_tokens_none_present(self):
        """Test hoạt động bình thường khi data ban đầu trống/không chứa token nào"""
        initial_data = {"user_id": 123}
        response = Response(data=initial_data)

        remove_tokens(response)

        assert response.data == {"user_id": 123}

    def test_clear_auth_cookies_sets_access_token_empty_and_expired(
        self, mock_auth_settings
    ):
        """Sau khi clear, access_token phải rỗng và max-age=0 (hết hạn ngay)"""
        response = Response(data={})

        clear_auth_cookies(response)

        access_name = mock_auth_settings["ACCESS_NAME"]
        access_cookie = response.cookies[access_name]

        assert access_cookie.value == ""
        assert access_cookie["max-age"] == 0

    def test_clear_auth_cookies_sets_refresh_token_empty_and_expired(
        self, mock_auth_settings
    ):
        """Sau khi clear, refresh_token phải rỗng và max-age=0 (hết hạn ngay)"""
        response = Response(data={})

        clear_auth_cookies(response)

        refresh_name = mock_auth_settings["REFRESH_NAME"]
        refresh_cookie = response.cookies[refresh_name]

        assert refresh_cookie.value == ""
        assert refresh_cookie["max-age"] == 0

    def test_clear_auth_cookies_uses_correct_path(self, mock_auth_settings):
        """Cookie xoá phải dùng đúng path đã cấu hình, để trình duyệt khớp đúng cookie cần xoá"""
        response = Response(data={})

        clear_auth_cookies(response)

        access_name = mock_auth_settings["ACCESS_NAME"]
        refresh_name = mock_auth_settings["REFRESH_NAME"]

        assert response.cookies[access_name]["path"] == mock_auth_settings["PATH"]
        assert response.cookies[refresh_name]["path"] == mock_auth_settings["PATH"]
