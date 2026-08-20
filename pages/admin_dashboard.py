import secrets
import string

import requests
import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="EduAI — Admin Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)


BACKEND_URL = "http://127.0.0.1:8000"

# n8n production webhook. Keep the n8n workflow ACTIVE.
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/send-instructor-credentials"
N8N_WEBHOOK_TIMEOUT = 15


# =========================================================
# RBAC
# =========================================================

if str(st.session_state.get("role", "")).upper() != "ADMIN":
    st.error("You do not have permission to access the Admin Dashboard.")

    if st.button("Back to Login"):
        st.session_state.clear()
        st.rerun()

    st.stop()


TOKEN = st.session_state.get("access_token", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


# =========================================================
# AUTOMATIC PASSWORD GENERATION
# =========================================================

def generate_secure_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    chars.extend(secrets.choice(alphabet) for _ in range(length - 4))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def trigger_n8n_instructor_email(name, email, password):
    return requests.post(
        N8N_WEBHOOK_URL,
        json={
            "name": name,
            "email": email,
            "username": email,
            "password": password,
        },
        headers={"Content-Type": "application/json"},
        timeout=N8N_WEBHOOK_TIMEOUT,
    )


# =========================================================
# API HELPERS
# =========================================================

def show_api_error(response):
    try:
        error = response.json().get(
            "detail",
            "Something went wrong",
        )
    except Exception:
        error = "Unable to connect with server"

    messages = {
        "Invalid email or password":
            "Incorrect email or password. Please check your details.",

        "Email already registered":
            "This email is already registered. Please use another email.",

        "Access denied":
            "You do not have permission to perform this action.",

        "Instructor not found":
            "Instructor record was not found.",

        "Course not found":
            "Course record was not found.",

        "Course is already assigned to this instructor.":
            "This course is already assigned to this instructor.",
    }

    st.error(
        "⚠️ " + messages.get(
            error,
            "Unable to complete your request. Please try again.",
        )
    )


def api_get(endpoint):
    return requests.get(
        f"{BACKEND_URL}{endpoint}",
        headers=HEADERS,
        timeout=10,
    )


def api_post(endpoint, payload):
    return requests.post(
        f"{BACKEND_URL}{endpoint}",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )


def api_delete(endpoint):
    return requests.delete(
        f"{BACKEND_URL}{endpoint}",
        headers=HEADERS,
        timeout=10,
    )


# =========================================================
# SESSION STATE
# =========================================================

if "admin_action" not in st.session_state:
    st.session_state.admin_action = None

if "instructor_result" not in st.session_state:
    st.session_state.instructor_result = None


# =========================================================
# GLOBAL UI
# Same visual style as the existing EduAI dashboard
# =========================================================

st.html(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600'
        '&family=Inter:wght@400;500;600'
        '&family=IBM+Plex+Mono:wght@500'
        '&display=swap'
    );


    /* =====================================================
       HIDE STREAMLIT DEFAULT UI
    ===================================================== */

    [data-testid="stSidebar"] {
        display: none !important;
    }

    [data-testid="collapsedControl"] {
        display: none !important;
    }

    header {
        display: none !important;
    }

    footer {
        display: none !important;
    }

    #MainMenu {
        visibility: hidden !important;
    }


    /* =====================================================
       PAGE
    ===================================================== */

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {

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
            #f8fafc;
    }


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
            #f8fafc;
    }


    .block-container {

        max-width: 1150px !important;

        padding-top: 5.5vh !important;

        padding-bottom: 35px !important;

        padding-left: 25px !important;

        padding-right: 25px !important;
    }


    /* =====================================================
       WELCOME
    ===================================================== */

    .welcome-section {

        text-align: center;

        margin-bottom: 24px;

        padding: 0 20px;
    }


    .welcome-eyebrow {

        display: inline-block;

        color: #4f46e5;

        background: #eef2ff;

        border: 1px solid #dbe4ff;

        border-radius: 999px;

        padding: 7px 14px;

        font-size: 11px;

        font-weight: 800;

        letter-spacing: 1.4px;

        text-transform: uppercase;

        margin-bottom: 10px;
    }


    .welcome-title {

        color: #0f172a;

        font-family: 'Inter', sans-serif;

        font-size: 32px;

        font-weight: 800;

        letter-spacing: -0.9px;

        line-height: 1.2;

        margin-bottom: 8px;
    }


    .welcome-description {

        color: #64748b;

        font-size: 14px;

        line-height: 1.7;

        max-width: 650px;

        margin: 0 auto;
    }


    /* =====================================================
       LOGOUT
    ===================================================== */

    .st-key-eduai_admin_logout button {

        min-height: 38px !important;

        height: 38px !important;

        width: auto !important;

        padding: 0 15px !important;

        border-radius: 10px !important;

        border: 1px solid #dbe3ed !important;

        background: rgba(255, 255, 255, 0.96) !important;

        color: #475569 !important;

        font-size: 12px !important;

        font-weight: 700 !important;

        box-shadow:
            0 4px 12px
            rgba(15, 23, 42, 0.055) !important;
    }


    .st-key-eduai_admin_logout {

        position: fixed;

        top: 18px;

        right: 24px;

        z-index: 999;
    }


    .st-key-eduai_admin_logout button:hover {

        color: #4f46e5 !important;

        border-color: #c7d2fe !important;

        background: #ffffff !important;
    }


    /* =====================================================
       CARD
    ===================================================== */

    .edu-card {

        background:
            rgba(255, 255, 255, 0.97);

        border:
            1px solid #e2e8f0;

        border-radius:
            24px;

        height:
            300px;

        padding:
            25px 28px 88px 28px;

        box-sizing:
            border-box;

        position:
            relative;

        overflow:
            hidden;

        box-shadow:
            0 12px 35px
            rgba(15, 23, 42, 0.065);

        transition:
            transform 0.25s ease,
            border-color 0.25s ease,
            box-shadow 0.25s ease;
    }


    .edu-card::before {

        content:
            "";

        position:
            absolute;

        top:
            0;

        left:
            0;

        width:
            100%;

        height:
            4px;

        background:
            linear-gradient(
                90deg,
                #6366f1,
                #3b82f6
            );

        opacity:
            0;

        transition:
            opacity 0.25s ease;
    }


    .edu-card:hover {

        transform:
            translateY(-6px);

        border-color:
            #c7d2fe;

        box-shadow:
            0 22px 48px
            rgba(15, 23, 42, 0.11);
    }


    .edu-card:hover::before {

        opacity:
            1;
    }


    /* =====================================================
       ICON
    ===================================================== */

    .edu-icon {

        width:
            58px;

        height:
            58px;

        display:
            flex;

        align-items:
            center;

        justify-content:
            center;

        border-radius:
            17px;

        font-size:
            27px;

        font-weight:
            700;

        margin-bottom:
            20px;
    }


    .instructor-icon {

        background:
            #eef2ff;

        color:
            #4f46e5;
    }


    .course-icon {

        background:
            #ecfdf5;

        color:
            #059669;
    }


    .assignment-icon {

        background:
            #fff7ed;

        color:
            #ea580c;
    }


    /* =====================================================
       CARD TITLE
    ===================================================== */

    .edu-title {

        color:
            #0f172a;

        font-size:
            20px;

        font-weight:
            750;

        letter-spacing:
            -0.35px;

        line-height:
            1.3;

        margin-bottom:
            15px;
    }


    /* =====================================================
       DESCRIPTION
    ===================================================== */

    .edu-description {

        color:
            #64748b;

        font-size:
            14px;

        line-height:
            1.65;

        max-width:
            100%;
    }


    /* =====================================================
       CARD BUTTON
    ===================================================== */

    [data-testid="column"] .stButton {

        margin-top:
            -70px !important;

        padding-left:
            18px !important;

        padding-right:
            18px !important;

        position:
            relative;

        z-index:
            20;
    }


    [data-testid="column"] .stButton > button {

        width:
            100% !important;

        height:
            46px !important;

        min-height:
            46px !important;

        border-radius:
            12px !important;

        border:
            1px solid #dbe3ee !important;

        background:
            #ffffff !important;

        color:
            #334155 !important;

        font-size:
            13.5px !important;

        font-weight:
            650 !important;

        box-shadow:
            0 3px 10px
            rgba(15, 23, 42, 0.045) !important;

        transition:
            all 0.20s ease !important;
    }


    [data-testid="column"] .stButton > button:hover {

        background:
            #4f46e5 !important;

        color:
            #ffffff !important;

        border-color:
            #4f46e5 !important;

        transform:
            translateY(-2px);

        box-shadow:
            0 8px 20px
            rgba(79, 70, 229, 0.18) !important;
    }


    [data-testid="column"] .stButton > button:active {

        transform:
            translateY(0);

        background:
            #4338ca !important;
    }


    [data-testid="column"] {

        display:
            flex;

        flex-direction:
            column;
    }


    /* =====================================================
       INNER ACTION PAGE
    ===================================================== */

    .action-page {

        background:
            rgba(255, 255, 255, 0.97);

        border:
            1px solid #e2e8f0;

        border-radius:
            24px;

        padding:
            30px;

        box-shadow:
            0 12px 35px
            rgba(15, 23, 42, 0.065);
    }


    .action-title {

        color:
            #0f172a;

        font-size:
            26px;

        font-weight:
            800;

        margin-bottom:
            8px;
    }


    .action-description {

        color:
            #64748b;

        font-size:
            14px;

        line-height:
            1.6;

        margin-bottom:
            22px;
    }


    /* =====================================================
       INPUTS
    ===================================================== */

    .stTextInput input,
    .stTextArea textarea {

        background:
            #ffffff !important;

        color:
            #0f172a !important;

        border:
            1px solid #dbe3ed !important;

        border-radius:
            10px !important;
    }


    .stTextInput label,
    .stTextArea label,
    [data-testid="stSelectbox"] label {

        color:
            #334155 !important;

        font-weight:
            600 !important;
    }


    div[data-baseweb="select"] > div {

        background:
            #ffffff !important;

        color:
            #0f172a !important;

        border:
            1px solid #dbe3ed !important;

        border-radius:
            10px !important;
    }


    div[data-baseweb="popover"],
    ul[role="listbox"] {

        background:
            #ffffff !important;
    }


    ul[role="listbox"] li {

        color:
            #0f172a !important;
    }


    /* =====================================================
       FORM BUTTON
    ===================================================== */

    div.stFormSubmitButton > button {

        background:
            #4f46e5 !important;

        color:
            #ffffff !important;

        border:
            1px solid #4f46e5 !important;

        border-radius:
            10px !important;

        font-weight:
            700 !important;
    }


    div.stFormSubmitButton > button:hover {

        background:
            #4338ca !important;
    }


    /* =====================================================
       NORMAL BUTTONS
    ===================================================== */

    .normal-action-button div.stButton > button {

        background:
            #ffffff !important;

        color:
            #334155 !important;

        border:
            1px solid #dbe3ed !important;

        border-radius:
            10px !important;
    }


    .normal-action-button div.stButton > button:hover {

        background:
            #4f46e5 !important;

        color:
            #ffffff !important;

        border-color:
            #4f46e5 !important;
    }


    /* =====================================================
       ASSIGNMENT RECORD
    ===================================================== */

    .assignment-record {

        background:
            #ffffff;

        border:
            1px solid #e2e8f0;

        border-radius:
            12px;

        padding:
            13px 16px;

        margin-bottom:
            8px;

        color:
            #334155;

        font-size:
            14px;

        box-shadow:
            0 3px 10px
            rgba(15, 23, 42, 0.035);
    }


    .assignment-instructor {

        color:
            #4f46e5;

        font-weight:
            700;
    }


    .assignment-arrow {

        color:
            #94a3b8;

        padding:
            0 8px;
    }


    .assignment-course {

        color:
            #334155;

        font-weight:
            600;
    }


    /* =====================================================
       INSTRUCTOR RESULT
    ===================================================== */

    .instructor-result {
        margin: 22px 0 10px 0;
        padding: 18px 22px;
        border-radius: 14px;
        background: #ecfdf5;
        border: 1px solid #bbf7d0;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
    }

    .instructor-result-title {
        color: #166534;
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .instructor-result-text {
        color: #166534;
        font-size: 13px;
        line-height: 1.6;
    }

    .instructor-result-email {
        color: #14532d;
        font-weight: 700;
    }


    /* =====================================================
       RESPONSIVE
    ===================================================== */

    @media (max-width: 900px) {

        .block-container {

            padding-top:
                7vh !important;

            padding-left:
                20px !important;

            padding-right:
                20px !important;
        }


        .welcome-title {

            font-size:
                30px;
        }


        .edu-card {

            height:
                285px;

            margin-bottom:
                25px;
        }
    }


    @media (max-width: 640px) {

        .welcome-title {

            font-size:
                26px;
        }


        .welcome-description {

            font-size:
                14px;
        }


        .edu-card {

            height:
                280px;

            padding:
                28px 25px 100px 25px;
        }


        .edu-title {

            font-size:
                19px;
        }


        .edu-description {

            font-size:
                13.5px;
        }
    }

    </style>
    """
)


# =========================================================
# LOGOUT
# =========================================================

if st.button(
    "Logout",
    key="eduai_admin_logout",
):
    st.session_state.clear()
    st.rerun()


# =========================================================
# MAIN DASHBOARD
# =========================================================

if st.session_state.admin_action is None:

    # -----------------------------------------------------
    # WELCOME
    # -----------------------------------------------------

    st.html(
        """
        <div class="welcome-section">

            <div class="welcome-eyebrow">
                EDUAI ADMIN DASHBOARD
            </div>

            <div class="welcome-title">
                Welcome to EduAI
            </div>

            <div class="welcome-description">
                Manage instructors, create courses, and assign
                courses to instructors from one place.
            </div>

        </div>
        """
    )


    # -----------------------------------------------------
    # THREE CARDS
    # -----------------------------------------------------

    col1, col2, col3 = st.columns(
        3,
        gap="large",
    )


    # =====================================================
    # CREATE INSTRUCTOR
    # =====================================================

    with col1:

        st.html(
            """
            <div class="edu-card">

                <div class="edu-icon instructor-icon">
                    ♙
                </div>

                <div class="edu-title">
                    Create Instructor
                </div>

                <div class="edu-description">
                    Create instructor accounts and add
                    instructors to the EduAI platform.
                </div>

            </div>
            """
        )


        if st.button(
            "Create Instructor  →",
            key="create_instructor",
            use_container_width=True,
        ):

            st.session_state.admin_action = "instructor"

            st.rerun()


    # =====================================================
    # CREATE COURSE
    # =====================================================

    with col2:

        st.html(
            """
            <div class="edu-card">

                <div class="edu-icon course-icon">
                    ▤
                </div>

                <div class="edu-title">
                    Create Course
                </div>

                <div class="edu-description">
                    Create courses and add them to the
                    EduAI course catalog.
                </div>

            </div>
            """
        )


        if st.button(
            "Create Course  →",
            key="create_course",
            use_container_width=True,
        ):

            st.session_state.admin_action = "course"

            st.rerun()


    # =====================================================
    # ASSIGN COURSE
    # =====================================================

    with col3:

        st.html(
            """
            <div class="edu-card">

                <div class="edu-icon assignment-icon">
                    ↔
                </div>

                <div class="edu-title">
                    Assign Course
                </div>

                <div class="edu-description">
                    Assign an existing course to an
                    instructor using simple selection.
                </div>

            </div>
            """
        )


        if st.button(
            "Assign Course  →",
            key="assign_course",
            use_container_width=True,
        ):

            st.session_state.admin_action = "assignment"

            st.rerun()


    st.stop()


# =========================================================
# ACTION PAGE
# =========================================================

action = st.session_state.admin_action


# =========================================================
# BACK TO DASHBOARD
# =========================================================

st.markdown(
    '<div class="normal-action-button">',
    unsafe_allow_html=True,
)

if st.button(
    "← Back to Dashboard",
    key="back_to_dashboard",
):

    st.session_state.admin_action = None

    st.rerun()

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


st.write("")

# Persistent instructor creation result.
# This remains visible after the Streamlit form reruns.
if st.session_state.get("instructor_result"):
    result = st.session_state.instructor_result

    st.html(
        f"""
        <div class="instructor-result">
            <div class="instructor-result-title">
                ✓ Instructor Created Successfully
            </div>
            <div class="instructor-result-text">
                <strong>{result["name"]}</strong> has been created successfully.
                Login credentials were sent to
                <span class="instructor-result-email">
                    {result["email"]}
                </span>.
            </div>
        </div>
        """
    )

    # Show it once, then clear it on the next rerun.
    st.session_state.instructor_result = None


# =========================================================
# CREATE INSTRUCTOR
# =========================================================

if action == "instructor":

    st.html(
        """
        <div class="action-page">

            <div class="action-title">
                Create Instructor
            </div>

            <div class="action-description">
                Create an instructor account for the EduAI platform.
            </div>

        </div>
        """
    )


    with st.form(
        "create_instructor_form",
        clear_on_submit=True,
    ):

        col1, col2 = st.columns(2)

        with col1:

            name = st.text_input(
                "Full Name"
            )

        with col2:

            email = st.text_input(
                "Email"
            )

        st.info(
            "A secure password will be generated automatically "
            "and sent to the instructor by email."
        )


        submitted = st.form_submit_button(
            "Create Instructor",
            use_container_width=True,
        )


    if submitted:

        if (
            not name.strip()
            or not email.strip()
        ):

            st.warning(
                "Please fill all required fields."
            )

        else:

            try:

                generated_password = generate_secure_password()

                response = api_post(
                    "/admin/create-instructor",
                    {
                        "name": name.strip(),
                        "email": email.strip(),
                        "password": generated_password,
                    },
                )


                if response.status_code == 200:

                    try:
                        n8n_response = trigger_n8n_instructor_email(
                            name=name.strip(),
                            email=email.strip(),
                            password=generated_password,
                        )

                        if 200 <= n8n_response.status_code < 300:
                            st.session_state.instructor_result = {
                                "name": name.strip(),
                                "email": email.strip(),
                            }
                            st.rerun()
                        else:
                            st.session_state.instructor_result = None
                            st.warning(
                                f"Instructor '{name}' was created, "
                                "but the credentials email could not be sent."
                            )
                            st.caption(
                                f"n8n error ({n8n_response.status_code}): "
                                f"{n8n_response.text[:500]}"
                            )

                    except requests.exceptions.RequestException as n8n_error:
                        st.warning(
                            f"Instructor '{name}' was created, "
                            "but the credentials email could not be sent."
                        )
                        st.caption(f"Could not connect to n8n: {n8n_error}")

                else:

                    show_api_error(response)


            except requests.exceptions.RequestException:

                st.error(
                    "Unable to connect with the backend."
                )


# =========================================================
# CREATE COURSE
# =========================================================

elif action == "course":

    st.html(
        """
        <div class="action-page">

            <div class="action-title">
                Create Course
            </div>

            <div class="action-description">
                Add a new course to the EduAI course catalog.
            </div>

        </div>
        """
    )


    with st.form(
        "create_course_form",
        clear_on_submit=True,
    ):

        name = st.text_input(
            "Course Name"
        )


        description = st.text_area(
            "Course Description"
        )


        submitted = st.form_submit_button(
            "Create Course",
            use_container_width=True,
        )


    if submitted:

        if not name.strip():

            st.warning(
                "Course name is required."
            )

        else:

            try:

                response = api_post(
                    "/admin/create-course",
                    {
                        "name": name.strip(),
                        "description":
                            description.strip()
                            or None,
                    },
                )


                if response.status_code == 200:

                    st.success(
                        f"Course '{name}' created successfully."
                    )

                else:

                    show_api_error(response)


            except requests.exceptions.RequestException:

                st.error(
                    "Unable to connect with the backend."
                )


# =========================================================
# ASSIGN COURSE
# =========================================================

elif action == "assignment":

    st.html(
        """
        <div class="action-page">

            <div class="action-title">
                Assign Course
            </div>

            <div class="action-description">
                Select an instructor and an existing course
                to create the course assignment.
            </div>

        </div>
        """
    )


    try:

        instructor_response = api_get(
            "/admin/instructors"
        )


        course_response = api_get(
            "/admin/courses"
        )


        if instructor_response.status_code != 200:

            show_api_error(
                instructor_response
            )

            st.stop()


        if course_response.status_code != 200:

            show_api_error(
                course_response
            )

            st.stop()


        instructors = instructor_response.json()

        courses = course_response.json()


    except requests.exceptions.RequestException:

        st.error(
            "Unable to connect with the backend."
        )

        st.stop()


    if not instructors:

        st.info(
            "No instructors are available. "
            "Create an instructor first."
        )


    elif not courses:

        st.info(
            "No courses are available. "
            "Create a course first."
        )


    else:

        instructor_map = {
            f"{item['name']} — {item['email']}":
            item["id"]

            for item in instructors
        }


        course_map = {
            f"{item['name']} — ID {item['id']}":
            item["id"]

            for item in courses
        }


        col1, col2 = st.columns(2)


        with col1:

            selected_instructor = st.selectbox(
                "Instructor",
                list(instructor_map.keys()),
            )


        with col2:

            selected_course = st.selectbox(
                "Course",
                list(course_map.keys()),
            )


        if st.button(
            "Assign Course",
            use_container_width=True,
        ):

            try:

                response = api_post(
                    "/admin/assign-course",
                    {
                        "instructor_id":
                            instructor_map[
                                selected_instructor
                            ],

                        "course_id":
                            course_map[
                                selected_course
                            ],
                    },
                )


                if response.status_code == 200:

                    st.success(
                        "Course assigned successfully."
                    )

                else:

                    show_api_error(
                        response
                    )


            except requests.exceptions.RequestException:

                st.error(
                    "Unable to connect with the backend."
                )


    # -----------------------------------------------------
    # CURRENT ASSIGNMENTS
    # -----------------------------------------------------

    st.write("")

    st.html(
        """
        <div class="action-title"
             style="font-size:20px;margin-top:25px;">
            Current Assignments
        </div>
        """
    )


    try:

        assignment_response = api_get(
            "/admin/assignments"
        )


        if assignment_response.status_code == 200:

            assignments = assignment_response.json()


            if not assignments:

                st.caption(
                    "No course assignments yet."
                )

            else:

                for assignment in assignments:

                    st.html(
                        f"""
                        <div class="assignment-record">

                            <span class="assignment-instructor">
                                {assignment['instructor_name']}
                            </span>

                            <span class="assignment-arrow">
                                →
                            </span>

                            <span class="assignment-course">
                                {assignment['course_name']}
                            </span>

                        </div>
                        """
                    )

        else:

            show_api_error(
                assignment_response
            )


    except requests.exceptions.RequestException:

        st.error(
            "Unable to connect with the backend."
        )