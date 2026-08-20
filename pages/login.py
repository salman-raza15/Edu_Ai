import requests
import streamlit as st

st.set_page_config(page_title="EduAI — Login", page_icon="📖", layout="wide")

API_BASE_URL = "http://127.0.0.1:8000"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');
:root{--ink:#20232A;--muted:#6B7280;--purple:#6F63D9;--purple-dark:#5B50C8;--border:#E2E4EA;--bg:#F6F7FA;--surface:#FFFFFF;}
.stApp{background:radial-gradient(circle at 20% 15%,rgba(111,99,217,.10),transparent 30%),radial-gradient(circle at 80% 85%,rgba(111,99,217,.07),transparent 30%),var(--bg);}
.stApp p,.stApp span,.stApp label,.stApp div{font-family:'Inter',sans-serif;}
h1,h2,h3{font-family:'Fraunces',serif!important;color:var(--ink)!important;}
[data-testid="stTextInput"] input{background:#fff!important;color:var(--ink)!important;border:1px solid var(--border)!important;border-radius:8px!important;min-height:44px!important;}
[data-testid="stTextInput"] label{color:var(--ink)!important;font-weight:500!important;}
div[data-baseweb="select"]>div{background:#fff!important;color:var(--ink)!important;border:1px solid var(--border)!important;border-radius:8px!important;min-height:44px!important;}
div[data-baseweb="select"] span{color:var(--ink)!important;}
div[data-baseweb="popover"],ul[role="listbox"]{background:#fff!important;}
ul[role="listbox"] li{color:var(--ink)!important;}
div.stButton>button{font-family:'Inter',sans-serif;font-weight:600;border-radius:8px;border:1px solid var(--border);color:var(--ink)!important;background:#fff;min-height:44px;}
div.stButton>button:hover{border-color:var(--purple);color:var(--purple-dark)!important;}
div.stFormSubmitButton>button{background:var(--purple)!important;color:#fff!important;border:none!important;border-radius:8px!important;min-height:46px!important;font-weight:700!important;}
div.stFormSubmitButton>button:hover{background:var(--purple-dark)!important;}
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--surface)!important;border:1px solid var(--border)!important;border-top:4px solid var(--purple)!important;border-radius:12px!important;padding:1.35rem!important;}
.eduai-brand{text-align:center;margin-top:4rem;margin-bottom:1.5rem;}
.eduai-brand h1{font-size:2.25rem!important;margin:0!important;}
.eduai-brand div{color:var(--muted)!important;font-size:.9rem;margin-top:.25rem;}
.form-title{font-family:'Fraunces',serif;font-size:1.45rem;font-weight:600;color:var(--ink);margin-bottom:.2rem;}
.form-description{color:var(--muted)!important;font-size:.88rem;margin-bottom:1rem;}
.role-caption{color:var(--muted)!important;font-size:.85rem;margin-top:-.25rem;margin-bottom:.6rem;}
.account-note{text-align:center;color:var(--muted)!important;font-size:.8rem;margin-top:.8rem;}
</style>
""", unsafe_allow_html=True)

left, center, right = st.columns([1, 1.05, 1])

with center:
    st.markdown("""
    <div class="eduai-brand">
        <h1>EduAI</h1>
        <div>Intelligent Assessment Platform</div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="form-title">Sign In</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-description">Sign in to your EduAI account.</div>', unsafe_allow_html=True)

        role = st.selectbox(
            "Login as",
            ["Admin", "Instructor"],
            index=0,
            key="login_role",
        )

        if role == "Admin":
            st.markdown(
                '<div class="role-caption">Administrators can create instructor accounts and manage courses.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="role-caption">Instructor accounts are created by an administrator.</div>',
                unsafe_allow_html=True,
            )

        with st.form("common_login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email.strip() or not password:
                st.warning("Please enter your email and password.")
            else:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/auth/login",
                        json={"email": email.strip(), "password": password},
                        timeout=10,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        actual_role = str(data.get("role", "")).upper()
                        selected_role = role.upper()

                        if actual_role != selected_role:
                            st.error(
                                f"This account is not registered as a {role}."
                            )
                        else:
                            st.session_state.eduai_authenticated = True
                            st.session_state.eduai_user_id = data["user_id"]
                            st.session_state.user_id = data["user_id"]
                            st.session_state.name = data["name"]
                            st.session_state.role = actual_role
                            st.session_state.access_token = data["access_token"]

                            # Rebuild the main navigation using the authenticated role.
                            # This avoids switching to a page that is not registered
                            # in the current hidden navigation.
                            st.rerun()

                    else:
                        try:
                            detail = response.json().get("detail", "Invalid email or password.")
                        except Exception:
                            detail = "Invalid email or password."

                        if response.status_code == 404:
                            st.error("Login endpoint was not found. Make sure the EduAI Admin/RBAC backend is running on port 8000.")
                        else:
                            st.error(detail)

                except requests.exceptions.ConnectionError:
                    st.error("Can't reach the EduAI backend. Start the FastAPI server first.")
                except requests.exceptions.Timeout:
                    st.error("Server response timeout.")
                except requests.exceptions.RequestException:
                    st.error("Unable to contact the EduAI backend.")

        if role == "Admin":
            st.write("")
            if st.button("Create New Account", use_container_width=True):
                st.switch_page("pages/Admin_Signup.py")
        else:
            st.markdown(
                '<div class="account-note">Instructor accounts are created by Admin.</div>',
                unsafe_allow_html=True,
            )