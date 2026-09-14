"""실제 Credential Manager와 Supabase에 접속하지 않고 Desktop 인증을 검증한다."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktop_launcher.desktop_auth import (
    AuthenticatedSession,
    CredentialStoreError,
    DesktopLoginError,
    DesktopNetworkError,
    SessionTokens,
    StoredCredential,
    SupabaseDesktopAuth,
    acquire_access_token,
    logout_desktop,
    show_login_dialog,
)


class FakeWidget:
    def __init__(self, *_args: object, **_options: object) -> None:
        pass

    def pack(self, **_options: object) -> "FakeWidget":
        return self

    def focus_set(self) -> None:
        pass


class FakeWindow(FakeWidget):
    def title(self, _value: str) -> None:
        pass

    def geometry(self, _value: str) -> None:
        pass

    def resizable(self, _width: bool, _height: bool) -> None:
        pass

    def configure(self, **_options: object) -> None:
        pass

    def bind(self, *_args: object) -> None:
        pass

    def protocol(self, *_args: object) -> None:
        pass

    def destroy(self) -> None:
        pass

    def mainloop(self) -> None:
        pass


class FakeStringVar:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


def tokens(access: str = "access", refresh: str = "refresh") -> SessionTokens:
    return SessionTokens(access_token=access, refresh_token=refresh)


def login_result(email: str = "user@example.com") -> AuthenticatedSession:
    return AuthenticatedSession(email=email, tokens=tokens())


def test_no_credential_requires_login_and_saves_only_refresh_token() -> None:
    auth = Mock()
    store = Mock()
    store.load.return_value = None
    login = Mock(return_value=login_result())

    assert acquire_access_token(auth, store, login, logger=Mock()) == "access"
    login.assert_called_once_with(auth, "")
    store.save.assert_called_once_with("user@example.com", "refresh")


def test_credential_refresh_returns_access_and_rotates_refresh_token() -> None:
    auth = Mock()
    auth.refresh.return_value = tokens("new-access", "rotated-refresh")
    store = Mock()
    store.load.return_value = StoredCredential("user@example.com", "stored-refresh")
    login = Mock()

    assert acquire_access_token(auth, store, login, logger=Mock()) == "new-access"
    auth.refresh.assert_called_once_with("stored-refresh")
    store.save.assert_called_once_with("user@example.com", "rotated-refresh")
    login.assert_not_called()


def test_refresh_failure_deletes_credential_and_falls_back_to_login() -> None:
    auth = Mock()
    auth.refresh.side_effect = DesktopLoginError("invalid")
    store = Mock()
    store.load.return_value = StoredCredential("user@example.com", "expired-refresh")
    login = Mock(return_value=login_result())

    assert acquire_access_token(auth, store, login, logger=Mock()) == "access"
    store.delete.assert_called_once_with()
    login.assert_called_once_with(auth, "user@example.com")


def test_refresh_network_failure_preserves_credential_during_login_fallback() -> None:
    auth = Mock()
    auth.refresh.side_effect = DesktopNetworkError("offline")
    store = Mock()
    store.load.return_value = StoredCredential("user@example.com", "stored-refresh")

    assert acquire_access_token(auth, store, Mock(return_value=None), logger=Mock()) is None
    store.delete.assert_not_called()


def test_login_cancel_or_failure_does_not_save_credential() -> None:
    store = Mock()
    store.load.return_value = None

    assert acquire_access_token(Mock(), store, Mock(return_value=None), logger=Mock()) is None
    store.save.assert_not_called()


def test_secure_store_failure_never_falls_back_to_plaintext() -> None:
    store = Mock()
    store.load.side_effect = CredentialStoreError("unavailable")
    store.save.side_effect = CredentialStoreError("unavailable")

    assert acquire_access_token(Mock(), store, Mock(return_value=login_result()), logger=Mock()) == "access"


def test_logout_deletes_desktop_credential() -> None:
    store = Mock()
    logout_desktop(store, logger=Mock())
    store.delete.assert_called_once_with()


def test_supabase_sdk_password_login_and_refresh_methods() -> None:
    sdk = Mock()
    sdk.auth.sign_in_with_password.return_value = SimpleNamespace(
        session=SimpleNamespace(access_token="login-access", refresh_token="login-refresh")
    )
    sdk.auth.refresh_session.return_value = SimpleNamespace(
        session=SimpleNamespace(access_token="fresh-access", refresh_token="fresh-refresh")
    )
    with patch("desktop_launcher.desktop_auth.create_client", return_value=sdk):
        auth = SupabaseDesktopAuth("https://project.supabase.co", "publishable-key")

    assert auth.sign_in("user@example.com", "not-saved-password") == tokens("login-access", "login-refresh")
    assert auth.refresh("stored-refresh") == tokens("fresh-access", "fresh-refresh")
    sdk.auth.sign_in_with_password.assert_called_once_with(
        {"email": "user@example.com", "password": "not-saved-password"}
    )
    sdk.auth.refresh_session.assert_called_once_with("stored-refresh")


def test_login_dialog_builds_labels_with_default_and_override_colors() -> None:
    label_factory = Mock(side_effect=FakeWidget)
    fake_tkinter = SimpleNamespace(
        Tk=FakeWindow,
        StringVar=FakeStringVar,
        Label=label_factory,
        Entry=FakeWidget,
        Button=FakeWidget,
    )

    with patch.dict(sys.modules, {"tkinter": fake_tkinter}):
        assert show_login_dialog(Mock()) is None

    label_colors = [call.kwargs["fg"] for call in label_factory.call_args_list]
    assert "#f5f7f3" in label_colors
    assert "#b7ff63" in label_colors
    assert "#8f9a94" in label_colors
