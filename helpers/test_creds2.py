import streamlit as st

from utils.gmail_creds import GmailOAuthManager, TokenStore, OAuthSettings

TOKEN_FILE = (Path(__file__).parent / ".tokens" / "gmail.json")



def main() -> None:
    st.set_page_config(page_title="Gmail Search", layout="wide")
    manager = GmailOAuthManager(OAuthSettings.from_secrets(), TokenStore(TOKEN_FILE))

    # Read query parameters in a way that works across Streamlit versions
    if hasattr(st, "query_params"):
        raw_params = dict(st.query_params)
    else:
        raw_params = st.experimental_get_query_params()

    # Normalize: convert list values (from experimental API) to single strings
    params = {k: (v if isinstance(v, str) else (v[0] if v else "")) for k, v in raw_params.items()}
    print(f"DEBUG: {params=}")
    print(f"DEBUG: token_path={TOKEN_FILE.resolve()}")

    if "code" in params and "state" in params:
        manager.exchange_code(params)
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
            else:
                st.experimental_set_query_params()
        except Exception:
            pass
        st.rerun()
    creds = manager.credentials()
    if not creds:
        st.header("Authorize Gmail Read-Only Access")
        try:
            url = manager.authorization_url()
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.link_button("Authorize with Google", url=url)
        return
    with st.sidebar.expander("Reset authorization", expanded=False):
        if st.button("Reset now"):
            manager.reset()
            st.success("Authorization removed.")
            st.rerun()
    st.success("Authorization active. Refresh tokens will be managed automatically.")
    st.caption(f"Token file path: {TOKEN_FILE.resolve()}")
    st.caption(f"Token file exists: {TOKEN_FILE.exists()}")


if __name__ == "__main__":
    main()
