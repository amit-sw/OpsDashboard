import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
)
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

PENDING_DIR = (Path(__file__).parent / ".tokens" / "pending")
STATE_KEY = "gmail_oauth_state"
PKCE_KEY = "gmail_oauth_pkce"


@dataclass
class OAuthSettings:
    client_id: str
    client_secret: Optional[str]
    redirect_uri: str

    @classmethod
    def from_secrets(cls) -> "OAuthSettings":
        cfg = st.secrets.get("gmail_oauth", {})
        return cls(
            client_id=cfg.get("client_id", ""),
            client_secret=cfg.get("client_secret"),
            redirect_uri=cfg.get("redirect_uri", ""),
        )


class TokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[Dict[str, str]]:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save(self, data: Dict[str, str]) -> None:
        try:
            payload = json.dumps(data)
            self.path.write_text(payload, encoding="utf-8")
            print(f"DEBUG: wrote tokens to {self.path.resolve()} (bytes={len(payload)})")
        except Exception as e:
            print(f"DEBUG: failed to write token file: {e}")
            raise

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


class SupabaseTokenStore:
    def __init__(self, supabase_client) -> None:
        self.client = supabase_client

    def load(self) -> Optional[Dict[str, str]]:
        record = self.client.get_token_from_db()
        if not record:
            return None
        token_data = record.get('token')
        if isinstance(token_data, dict):
            return token_data
        if isinstance(token_data, str):
            try:
                return json.loads(token_data)
            except Exception:
                return None
        return None

    def save(self, data: Dict[str, str]) -> None:
        self.client.set_token_in_db(data)

    def clear(self) -> None:
        self.client.set_token_in_db(None)


def pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


class PendingAuthStore:
    def __init__(self, dir_path: Path) -> None:
        self.dir = dir_path
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, state: str) -> Path:
        return self.dir / f"{state}.json"

    def save(self, state: str, verifier: str) -> None:
        data = {"verifier": verifier, "ts": int(time.time())}
        self._path(state).write_text(json.dumps(data), encoding="utf-8")
        print(f"DEBUG: saved pending verifier for state={state} → {self._path(state).resolve()}")

    def load(self, state: str) -> Optional[str]:
        p = self._path(state)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("verifier")
        except Exception:
            return None

    def clear(self, state: str) -> None:
        p = self._path(state)
        if p.exists():
            p.unlink()


class GmailOAuthManager:
    def __init__(self, settings: OAuthSettings, store: TokenStore) -> None:
        self.settings = settings
        self.store = store
        self._tokens = store.load()
        self._creds = self._creds_from_tokens(self._tokens)
        self._pending = PendingAuthStore(PENDING_DIR)
        # If we have a client_secret (confidential client), prefer no-PKCE; otherwise use PKCE
        self._use_pkce = not bool(self.settings.client_secret)
        print(f"DEBUG: use_pkce={self._use_pkce}")

    def _creds_from_tokens(self, tokens: Optional[Dict[str, str]]) -> Optional[Credentials]:
        if not tokens:
            return None
        try:
            return Credentials.from_authorized_user_info(tokens, SCOPES)
        except Exception:
            self.store.clear()
            return None

    def authorization_url(self) -> str:
        self._assert_config()
        verifier = None
        code_challenge = None
        if self._use_pkce:
            verifier, code_challenge = pkce_pair()
            st.session_state[PKCE_KEY] = verifier
        oauth = OAuth2Session(
            client_id=self.settings.client_id,
            scope=SCOPES,
            redirect_uri=self.settings.redirect_uri,
            code_challenge=code_challenge if self._use_pkce else None,
            code_challenge_method="S256" if self._use_pkce else None,
        )
        url, state = oauth.create_authorization_url(
            AUTH_URI,
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        st.session_state[STATE_KEY] = state
        if self._use_pkce and verifier:
            try:
                self._pending.save(state, verifier)
            except Exception as e:
                print(f"DEBUG: failed to persist pending verifier: {e}")
        print(f"DEBUG: authorization_url: {url}")
        return url

    def exchange_code(self, params: Dict[str, str]) -> None:
        incoming_state = params.get("state")
        if not incoming_state:
            st.error("Invalid authorization response (missing state). Please retry.")
            return
        code = params.get("code")
        if not code:
            st.error("Missing authorization code.")
            return

        # Try to load PKCE verifier if we used PKCE for this flow; otherwise proceed without it
        verifier = st.session_state.get(PKCE_KEY)
        if not verifier:
            recovered = self._pending.load(incoming_state)
            if recovered:
                verifier = recovered
                print("DEBUG: recovered PKCE verifier from pending store")
        # If still no verifier, we'll request token without code_verifier

        # Optionally verify state if we still have it in session (may be absent after redirect)
        if st.session_state.get(STATE_KEY) and incoming_state != st.session_state.get(STATE_KEY):
            print("DEBUG: state mismatch; continuing")

        session = OAuth2Session(
            client_id=self.settings.client_id,
            scope=SCOPES,
            redirect_uri=self.settings.redirect_uri,
        )
        try:
            kwargs = {
                "code": code,
                "client_secret": self.settings.client_secret,
            }
            if verifier:
                kwargs["code_verifier"] = verifier
            token = session.fetch_token(TOKEN_URI, **kwargs)
            print(f"DEBUG: fetch_token() keys={list(token.keys())}; used_pkce={bool(verifier)}")
        except Exception as exc:
            err = f"Token exchange failed: {exc}"
            print(f"DEBUG: {err}")
            st.error(err)
            if "code_verifier" in str(exc) and "not needed" in str(exc):
                st.info("Retrying without PKCE may help if your OAuth client is a Web application with a client secret.")
            return

        formatted = self._format_token(token)
        print(f"DEBUG: formatted token keys={list(formatted.keys())}")
        self.store.save(formatted)
        if hasattr(self.store, "path"):
            if not self.store.path.exists():
                st.error(f"Token file did not appear at {self.store.path.resolve()}")
                print("DEBUG: token file missing after save()")
                return
            st.success(f"Saved token file → {self.store.path.resolve()}")
        else:
            st.success("Saved token to secure store.")
        self._tokens = formatted
        self._creds = self._creds_from_tokens(formatted)

        # Clear any pending verifier for this state
        if verifier:
            try:
                self._pending.clear(incoming_state)
            except Exception as e:
                print(f"DEBUG: failed to clear pending verifier: {e}")

        self._cleanup_state()

    def credentials(self) -> Optional[Credentials]:
        if not self._creds:
            return None
        if self._creds.valid:
            return self._creds
        if self._creds.expired and self._creds.refresh_token:
            return self._refresh()
        return None

    def reset(self) -> None:
        self.store.clear()
        self._tokens = None
        self._creds = None
        self._cleanup_state()

    def _refresh(self) -> Optional[Credentials]:
        try:
            self._creds.refresh(Request())
            tokens = json.loads(self._creds.to_json())
            self.store.save(tokens)
            self._tokens = tokens
            return self._creds
        except Exception as exc:
            msg = str(exc)
            if "invalid_grant" in msg or "invalid_scope" in msg:
                self.reset()
                st.warning("Authorization expired. Please sign in again.")
                return None
            st.error(f"Token refresh failed: {exc}")
            return None

    def _cleanup_state(self) -> None:
        for key in (STATE_KEY, PKCE_KEY):
            if key in st.session_state:
                del st.session_state[key]

    def _format_token(self, token: Dict[str, str]) -> Dict[str, str]:
        data = {
            "token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "token_uri": TOKEN_URI,
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret or "",
            "scopes": SCOPES,
        }
        if token.get("id_token"):
            data["id_token"] = token.get("id_token")
        return data

    def _assert_config(self) -> None:
        if not self.settings.client_id or not self.settings.redirect_uri:
            raise RuntimeError("Missing OAuth configuration in secrets.")
