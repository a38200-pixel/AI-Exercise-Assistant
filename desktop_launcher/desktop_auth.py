"""Supabase Desktop authentication backed by Windows Credential Manager."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Protocol

import httpx
from supabase import create_client
from supabase_auth.errors import AuthError, AuthRetryableError


CREDENTIAL_TARGET = "FitRoute AI Client/supabase_refresh_token"
CREDENTIAL_TYPE_GENERIC = 1
CREDENTIAL_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168
MAX_CREDENTIAL_BLOB_BYTES = 2560


class DesktopAuthError(RuntimeError):
    """민감정보를 포함하지 않는 Desktop 인증 오류."""


class DesktopLoginError(DesktopAuthError):
    """로그인 또는 refresh credential이 유효하지 않음."""


class DesktopNetworkError(DesktopAuthError):
    """Supabase Auth에 연결할 수 없음."""


class CredentialStoreError(DesktopAuthError):
    """Windows Credential Manager를 사용할 수 없음."""


@dataclass(frozen=True)
class SessionTokens:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class StoredCredential:
    email: str
    refresh_token: str


@dataclass(frozen=True)
class AuthenticatedSession:
    email: str
    tokens: SessionTokens


class CredentialStore(Protocol):
    def load(self) -> StoredCredential | None: ...
    def save(self, email: str, refresh_token: str) -> None: ...
    def delete(self) -> None: ...


class CREDENTIALW(ctypes.Structure):
    _fields_ = (
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", wintypes.LPVOID),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    )


class WindowsCredentialStore:
    """Refresh token만 Generic Credential로 암호화 저장한다."""

    def __init__(self, target: str = CREDENTIAL_TARGET) -> None:
        self.target = target

    @staticmethod
    def _api() -> ctypes.WinDLL:
        if os.name != "nt":
            raise CredentialStoreError("Windows Credential Manager is unavailable.")
        return ctypes.WinDLL("Advapi32.dll", use_last_error=True)

    def load(self) -> StoredCredential | None:
        api = self._api()
        credential_pointer = ctypes.POINTER(CREDENTIALW)()
        cred_read = api.CredReadW
        cred_read.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
        )
        cred_read.restype = wintypes.BOOL
        if not cred_read(
            self.target,
            CREDENTIAL_TYPE_GENERIC,
            0,
            ctypes.byref(credential_pointer),
        ):
            if ctypes.get_last_error() == ERROR_NOT_FOUND:
                return None
            raise CredentialStoreError("Could not read the Desktop credential.")

        cred_free = api.CredFree
        cred_free.argtypes = (wintypes.LPVOID,)
        cred_free.restype = None
        try:
            credential = credential_pointer.contents
            token_bytes = ctypes.string_at(
                credential.CredentialBlob,
                credential.CredentialBlobSize,
            )
            return StoredCredential(
                email=credential.UserName or "",
                refresh_token=token_bytes.decode("utf-8"),
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise CredentialStoreError("Stored Desktop credential is invalid.") from exc
        finally:
            cred_free(credential_pointer)

    def save(self, email: str, refresh_token: str) -> None:
        token_bytes = refresh_token.encode("utf-8")
        if not token_bytes or len(token_bytes) > MAX_CREDENTIAL_BLOB_BYTES:
            raise CredentialStoreError("Desktop credential has an invalid size.")

        api = self._api()
        blob = (wintypes.BYTE * len(token_bytes)).from_buffer_copy(token_bytes)
        credential = CREDENTIALW()
        credential.Type = CREDENTIAL_TYPE_GENERIC
        credential.TargetName = self.target
        credential.CredentialBlobSize = len(token_bytes)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(wintypes.BYTE))
        credential.Persist = CREDENTIAL_PERSIST_LOCAL_MACHINE
        credential.UserName = email

        cred_write = api.CredWriteW
        cred_write.argtypes = (ctypes.POINTER(CREDENTIALW), wintypes.DWORD)
        cred_write.restype = wintypes.BOOL
        if not cred_write(ctypes.byref(credential), 0):
            raise CredentialStoreError("Could not save the Desktop credential.")

    def delete(self) -> None:
        api = self._api()
        cred_delete = api.CredDeleteW
        cred_delete.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
        cred_delete.restype = wintypes.BOOL
        if not cred_delete(self.target, CREDENTIAL_TYPE_GENERIC, 0):
            if ctypes.get_last_error() == ERROR_NOT_FOUND:
                return
            raise CredentialStoreError("Could not delete the Desktop credential.")


class SupabaseDesktopAuth:
    """프로젝트와 동일한 Supabase Auth client로 login/refresh를 수행한다."""

    def __init__(self, supabase_url: str, supabase_anon_key: str) -> None:
        self.client = create_client(supabase_url, supabase_anon_key)

    @staticmethod
    def _tokens(response: object) -> SessionTokens:
        session = getattr(response, "session", None)
        access_token = getattr(session, "access_token", "")
        refresh_token = getattr(session, "refresh_token", "")
        if not access_token or not refresh_token:
            raise DesktopLoginError("Supabase did not return a valid Desktop session.")
        return SessionTokens(access_token=access_token, refresh_token=refresh_token)

    def sign_in(self, email: str, password: str) -> SessionTokens:
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            return self._tokens(response)
        except (AuthRetryableError, httpx.RequestError) as exc:
            raise DesktopNetworkError("Could not connect to Supabase Auth.") from exc
        except AuthError as exc:
            raise DesktopLoginError("Desktop email or password is invalid.") from exc

    def refresh(self, refresh_token: str) -> SessionTokens:
        try:
            response = self.client.auth.refresh_session(refresh_token)
            return self._tokens(response)
        except (AuthRetryableError, httpx.RequestError) as exc:
            raise DesktopNetworkError("Could not connect to Supabase Auth.") from exc
        except AuthError as exc:
            raise DesktopLoginError("Stored Desktop session is invalid.") from exc


LoginCallback = Callable[[SupabaseDesktopAuth, str], AuthenticatedSession | None]


def acquire_access_token(
    auth: SupabaseDesktopAuth,
    credential_store: CredentialStore,
    login_callback: LoginCallback,
    *,
    logger: Callable[[str], None] = print,
) -> str | None:
    """Refresh를 우선 사용하고 실패하면 한 번의 사용자 login flow로 전환한다."""
    stored: StoredCredential | None = None
    try:
        stored = credential_store.load()
    except CredentialStoreError:
        logger("Desktop credential storage unavailable; login will be used for this run.")

    if stored is not None:
        logger("Desktop credential found.")
        try:
            tokens = auth.refresh(stored.refresh_token)
        except DesktopNetworkError:
            # 네트워크 오류는 credential 무효를 의미하지 않으므로 삭제하지 않는다.
            logger("Desktop session refresh unavailable. Desktop login required.")
        except DesktopLoginError:
            logger("Desktop session refresh failed. Desktop login required.")
            try:
                credential_store.delete()
            except CredentialStoreError:
                pass
        else:
            logger("Supabase session refreshed.")
            try:
                credential_store.save(stored.email, tokens.refresh_token)
            except CredentialStoreError:
                logger("Rotated credential could not be persisted; this login is temporary.")
            return tokens.access_token

    logger("Desktop login required.")
    login_result = login_callback(auth, stored.email if stored else "")
    if login_result is None:
        logger("Desktop login canceled.")
        return None

    # Callback 내부 password는 반환되지 않으며 refresh token만 Credential Manager에 저장한다.
    try:
        credential_store.save(login_result.email, login_result.tokens.refresh_token)
    except CredentialStoreError:
        logger("Desktop credential could not be persisted; this login is temporary.")
    logger("Desktop authentication succeeded.")
    return login_result.tokens.access_token


def show_login_dialog(auth: SupabaseDesktopAuth, initial_email: str = "") -> AuthenticatedSession | None:
    """대형 GUI dependency 없이 최초 인증에만 사용하는 작은 tkinter dialog."""
    import tkinter as tk

    result: AuthenticatedSession | None = None
    window = tk.Tk()
    window.title("FitRoute Desktop Login")
    window.geometry("440x470")
    window.resizable(False, False)
    window.configure(bg="#0b110e")

    email_var = tk.StringVar(value=initial_email)
    password_var = tk.StringVar()
    status_var = tk.StringVar()

    def label(text: str, **options: object) -> tk.Label:
        options.setdefault("bg", "#0b110e")
        options.setdefault("fg", "#f5f7f3")
        return tk.Label(window, text=text, **options)

    label("FitRoute.", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=36, pady=(34, 2))
    label("Desktop AI Client", font=("Segoe UI", 12, "bold"), fg="#b7ff63").pack(anchor="w", padx=36)
    label(
        "웹에서 로그인한 동일한 FitRoute 계정을 사용해주세요.",
        font=("Segoe UI", 9),
        fg="#8f9a94",
    ).pack(anchor="w", padx=36, pady=(10, 24))

    label("Email", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=36)
    email_entry = tk.Entry(window, textvariable=email_var, font=("Segoe UI", 11), relief="flat")
    email_entry.pack(fill="x", padx=36, ipady=9, pady=(7, 15))
    label("Password", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=36)
    password_entry = tk.Entry(window, textvariable=password_var, show="*", font=("Segoe UI", 11), relief="flat")
    password_entry.pack(fill="x", padx=36, ipady=9, pady=(7, 8))
    tk.Label(window, textvariable=status_var, bg="#0b110e", fg="#ffb4a9", font=("Segoe UI", 9)).pack(anchor="w", padx=36, pady=(3, 9))

    def submit() -> None:
        nonlocal result
        email = email_var.get().strip()
        password = password_var.get()
        if not email or not password:
            status_var.set("이메일과 비밀번호를 입력해주세요.")
            return
        status_var.set("로그인 중...")
        window.update_idletasks()
        try:
            result = AuthenticatedSession(email=email, tokens=auth.sign_in(email, password))
        except DesktopNetworkError:
            status_var.set("네트워크 연결을 확인해주세요.")
            return
        except DesktopLoginError:
            status_var.set("이메일 또는 비밀번호를 확인해주세요.")
            return
        finally:
            password_var.set("")
        window.destroy()

    login_button = tk.Button(
        window,
        text="로그인",
        command=submit,
        bg="#b7ff63",
        fg="#0b110e",
        activebackground="#c5ff82",
        relief="flat",
        font=("Segoe UI", 11, "bold"),
        cursor="hand2",
    )
    login_button.pack(fill="x", padx=36, ipady=9, pady=(7, 8))
    tk.Button(
        window,
        text="취소",
        command=window.destroy,
        bg="#0b110e",
        fg="#8f9a94",
        activebackground="#111a15",
        activeforeground="#f5f7f3",
        relief="flat",
        font=("Segoe UI", 9),
        cursor="hand2",
    ).pack(fill="x", padx=36, ipady=6)
    window.bind("<Return>", lambda _event: submit())
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    (email_entry if not initial_email else password_entry).focus_set()
    window.mainloop()
    return result


def logout_desktop(credential_store: CredentialStore, *, logger: Callable[[str], None] = print) -> None:
    credential_store.delete()
    logger("FitRoute Desktop session removed.")
