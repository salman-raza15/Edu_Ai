import requests
import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="EduAI — Admin Signup",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE_URL = "http://127.0.0.1:8000"


# =========================================================
# UI — ONE SINGLE FORM / CARD
# =========================================================

st.html(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600'
        '&family=Inter:wght@400;500;600'
        '&display=swap'
    );

    /* Hide Streamlit chrome */
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    header,
    footer {
        display: none !important;
    }

    #MainMenu {
        visibility: hidden !important;
    }

    /* Page background */
    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .stApp {
        min-height: 100vh !important;

        background:
            radial-gradient(
                circle at 14% 20%,
                rgba(99, 102, 241, 0.10),
                transparent 31%
            ),
            radial-gradient(
                circle at 86% 82%,
                rgba(59, 130, 246, 0.09),
                transparent 31%
            ),
            #f8fafc !important;
    }

    .block-container {
        max-width: 100% !important;
        padding-top: 5vh !important;
        padding-bottom: 35px !important;
    }

    /* Everything has one common width */
    .signup-wrapper {
        width: 620px;
        max-width: calc(100vw - 40px);
        margin: 0 auto;
    }

    /* Brand */
    .signup-brand {
        text-align: center;
        margin-bottom: 28px;
    }

    .signup-logo {
        color: #0f172a;
        font-family: 'Inter', sans-serif;
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -1px;
        line-height: 1.2;
        margin-bottom: 7px;
    }

    .signup-subtitle {
        color: #64748b;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 600;
    }

    /* THE ONLY CARD */
    div[data-testid="stForm"] {
        width: 620px !important;
        max-width: calc(100vw - 40px) !important;

        margin: 0 auto !important;

        padding: 32px 34px 30px 34px !important;

        box-sizing: border-box !important;

        background: rgba(255, 255, 255, 0.97) !important;

        border: 1px solid #e2e8f0 !important;

        border-radius: 24px !important;

        box-shadow:
            0 16px 42px
            rgba(15, 23, 42, 0.075) !important;

        position: relative;
        overflow: hidden;
    }

    /* Top gradient line */
    div[data-testid="stForm"]::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;

        background:
            linear-gradient(
                90deg,
                #6366f1,
                #3b82f6
            );
    }

    /* Form header */
    .form-icon {
        width: 58px;
        height: 58px;

        display: flex;
        align-items: center;
        justify-content: center;

        margin: 0 auto 20px auto;

        border-radius: 17px;

        background: #eef2ff;
        color: #4f46e5;

        font-size: 26px;
        font-weight: 700;
    }

    .form-title {
        color: #0f172a;

        font-family: 'Inter', sans-serif;

        font-size: 24px;
        font-weight: 800;

        letter-spacing: -0.5px;

        text-align: center;

        margin-bottom: 8px;
    }

    .form-description {
        color: #64748b;

        font-family: 'Inter', sans-serif;

        font-size: 13.5px;

        line-height: 1.65;

        text-align: center;

        margin-bottom: 24px;
    }

    /* Labels */
    div[data-testid="stForm"] .stTextInput label {
        color: #334155 !important;

        font-family: 'Inter', sans-serif !important;

        font-size: 13px !important;

        font-weight: 650 !important;
    }

    /* Inputs */
    div[data-testid="stForm"] .stTextInput {
        width: 100% !important;
        margin-bottom: 5px !important;
    }

    div[data-testid="stForm"] .stTextInput input {
        width: 100% !important;

        min-height: 44px !important;

        box-sizing: border-box !important;

        background: #ffffff !important;

        color: #0f172a !important;

        border: 1px solid #dbe3ed !important;

        border-radius: 10px !important;

        font-family: 'Inter', sans-serif !important;
    }

    div[data-testid="stForm"] .stTextInput input:focus {
        border-color: #818cf8 !important;

        box-shadow:
            0 0 0 3px
            rgba(99, 102, 241, 0.10) !important;
    }

    /* Submit button */
    div[data-testid="stForm"] div.stFormSubmitButton {
        width: 100% !important;
        margin-top: 12px !important;
    }

    div[data-testid="stForm"] div.stFormSubmitButton > button {
        width: 100% !important;

        height: 46px !important;
        min-height: 46px !important;

        border: 1px solid #4f46e5 !important;

        border-radius: 11px !important;

        background: #4f46e5 !important;

        color: #ffffff !important;

        font-family: 'Inter', sans-serif !important;

        font-size: 13.5px !important;

        font-weight: 750 !important;

        box-shadow:
            0 7px 18px
            rgba(79, 70, 229, 0.16) !important;

        transition: all 0.20s ease !important;
    }

    div[data-testid="stForm"] div.stFormSubmitButton > button:hover {
        background: #4338ca !important;

        border-color: #4338ca !important;

        transform: translateY(-2px);

        box-shadow:
            0 10px 22px
            rgba(79, 70, 229, 0.22) !important;
    }

    /* =====================================================
       BACK TO LOGIN — SAME WIDTH AS THE FORM
    ===================================================== */

    .st-key-back_to_login {
        width: 620px !important;
        max-width: calc(100vw - 40px) !important;

        margin: 14px auto 0 auto !important;
    }

    .st-key-back_to_login > div {
        width: 100% !important;
    }

    .st-key-back_to_login div.stButton {
        width: 100% !important;
        margin: 0 !important;
    }

    .st-key-back_to_login div.stButton > button {
        width: 100% !important;

        height: 42px !important;

        background: rgba(255, 255, 255, 0.96) !important;

        border: 1px solid #dbe3ed !important;

        border-radius: 10px !important;

        color: #64748b !important;

        font-family: 'Inter', sans-serif !important;

        font-size: 13px !important;

        font-weight: 600 !important;

        box-shadow:
            0 4px 12px
            rgba(15, 23, 42, 0.04) !important;
    }

    .st-key-back_to_login div.stButton > button:hover {
        color: #4f46e5 !important;

        background: #ffffff !important;

        border-color: #c7d2fe !important;

        transform: translateY(-1px);
    }

    /* Messages stay aligned with the form */
    div[data-testid="stAlert"] {
        width: 620px !important;
        max-width: calc(100vw - 40px) !important;

        margin-left: auto !important;
        margin-right: auto !important;

        border-radius: 10px !important;

        font-family: 'Inter', sans-serif !important;

        font-size: 13px !important;
    }

    @media (max-width: 640px) {

        .signup-wrapper,
        div[data-testid="stForm"],
        .st-key-back_to_login,
        div[data-testid="stAlert"] {

            width: calc(100vw - 36px) !important;

            max-width: calc(100vw - 36px) !important;
        }

        div[data-testid="stForm"] {
            padding: 28px 22px 26px 22px !important;
            border-radius: 20px !important;
        }

        .signup-logo {
            font-size: 30px;
        }

        .form-title {
            font-size: 22px;
        }
    }

    </style>
    """
)


# =========================================================
# BRAND
# =========================================================

st.html(
    """
    <div class="signup-brand">

        <div class="signup-logo">
            EduAI
        </div>

        <div class="signup-subtitle">
            Admin Console
        </div>

    </div>
    """
)


# =========================================================
# ONE SINGLE FORM
# =========================================================

with st.form(
    "admin_signup_form",
    clear_on_submit=False,
):

    st.html(
        """
        <div class="form-icon">
            ♙
        </div>

        <div class="form-title">
            Create Admin Account
        </div>

        <div class="form-description">
            Create an administrator account for the EduAI platform.
        </div>
        """
    )

    name = st.text_input(
        "Full Name"
    )

    email = st.text_input(
        "Email"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    submitted = st.form_submit_button(
        "Create Admin Account",
        use_container_width=True,
    )


# =========================================================
# SIGNUP LOGIC — UNCHANGED
# =========================================================

if submitted:

    if not name.strip() or not email.strip() or not password:

        st.warning(
            "Please fill all required fields."
        )

    elif len(password) < 6:

        st.warning(
            "Password must be at least 6 characters."
        )

    else:

        try:

            resp = requests.post(
                f"{API_BASE_URL}/auth/admin-signup",

                json={
                    "name": name.strip(),
                    "email": email.strip(),
                    "password": password,
                },

                timeout=10,
            )

            if resp.status_code == 200:

                st.success(
                    "Admin account created successfully."
                )

                st.info(
                    "You can now sign in with your admin credentials."
                )

            else:

                try:

                    detail = resp.json().get(
                        "detail",
                        "Unable to create account.",
                    )

                except Exception:

                    detail = "Unable to create account."

                st.error(detail)

        except requests.exceptions.ConnectionError:

            st.error(
                "Can't reach the backend. "
                "Start the FastAPI server first."
            )

        except requests.exceptions.Timeout:

            st.error(
                "Server response timeout."
            )


# =========================================================
# BACK TO LOGIN
# =========================================================

st.markdown(
    '<div class="back-login">',
    unsafe_allow_html=True,
)

if st.button(
    "← Back to Login",
    key="back_to_login",
    use_container_width=True,
):

    st.switch_page(
        "pages/login.py"
    )