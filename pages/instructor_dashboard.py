import os
import requests
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="EduAI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

EDUAI_AUTH_API_URL = os.getenv(
    "EDUAI_AUTH_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

if "eduai_authenticated" not in st.session_state:
    st.session_state.eduai_authenticated = False
if "eduai_login_error" not in st.session_state:
    st.session_state.eduai_login_error = None
if "eduai_access_token" not in st.session_state:
    st.session_state.eduai_access_token = st.session_state.get("access_token", "")
if "eduai_user_id" not in st.session_state:
    st.session_state.eduai_user_id = st.session_state.get("user_id")
if "eduai_user_name" not in st.session_state:
    st.session_state.eduai_user_name = st.session_state.get("name", "")
if "eduai_user_role" not in st.session_state:
    st.session_state.eduai_user_role = st.session_state.get("role", "")
if "selected_course_id" not in st.session_state:
    st.session_state.selected_course_id = None

question_generation_page = st.Page(
    "pages/Question_generation.py",
    title="Question Generation",
)
assignment_evaluation_page = st.Page(
    "pages/AI_Assignment_Evaluation.py",
    title="AI Assignment Evaluation",
)
report_generation_page = st.Page(
    "pages/Report_Generation.py",
    title="Report Generation",
)

if str(st.session_state.get("role", "")).upper() != "INSTRUCTOR":
    st.error("Instructor access required.")
    if st.button("Back to Login"):
        st.session_state.clear()
        st.switch_page("pages/login.py")
    st.stop()


def dashboard_page():

    # =====================================================
    # GLOBAL CSS
    # =====================================================

    st.html(
        """
        <style>

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


        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {

            height:
                100vh !important;

            max-height:
                100vh !important;

            overflow:
                hidden !important;
        }


        [data-testid="stMainBlockContainer"] {

            height:
                100vh !important;

            max-height:
                100vh !important;

            overflow:
                hidden !important;
        }


        /* =====================================================
           PAGE BACKGROUND
        ===================================================== */

        .stApp {

            height:
                100vh !important;

            min-height:
                100vh !important;

            overflow:
                hidden !important;

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


        /* =====================================================
           MAIN CONTAINER
        ===================================================== */

        .block-container {

            max-width: 1150px !important;

            padding-top: 5.5vh !important;
            padding-bottom: 18px !important;

            padding-left: 25px !important;
            padding-right: 25px !important;
        }


        /* =====================================================
           WELCOME SECTION
        ===================================================== */

        .welcome-section {

            text-align:
                center;

            margin-bottom:
                24px;

            padding:
                0 20px;
        }


        .welcome-eyebrow {

            display:
                inline-block;

            color:
                #4f46e5;

            background:
                #eef2ff;

            border:
                1px solid #dbe4ff;

            border-radius:
                999px;

            padding:
                7px 14px;

            font-size:
                11px;

            font-weight:
                800;

            letter-spacing:
                1.4px;

            text-transform:
                uppercase;

            margin-bottom:
                10px;
        }


        .welcome-title {

            color:
                #0f172a;

            font-size:
                32px;

            font-weight:
                800;

            letter-spacing:
                -0.9px;

            line-height:
                1.2;

            margin-bottom:
                8px;
        }


        .welcome-description {

            color:
                #64748b;

            font-size:
                14px;

            line-height:
                1.7;

            max-width:
                650px;

            margin:
                0 auto;
        }


        /* =====================================================
           LOGOUT BUTTON
        ===================================================== */

        .st-key-eduai_logout_button {

            position:
                fixed;

            top:
                18px;

            right:
                24px;

            z-index:
                999;
        }


        .st-key-eduai_logout_button button {

            min-height:
                38px !important;

            height:
                38px !important;

            width:
                auto !important;

            padding:
                0 15px !important;

            border-radius:
                10px !important;

            border:
                1px solid #dbe3ed !important;

            background:
                rgba(255, 255, 255, 0.96) !important;

            color:
                #475569 !important;

            font-size:
                12px !important;

            font-weight:
                700 !important;

            box-shadow:
                0 4px 12px
                rgba(15, 23, 42, 0.055) !important;
        }


        .st-key-eduai_logout_button button:hover {

            color:
                #4f46e5 !important;

            border-color:
                #c7d2fe !important;

            background:
                #ffffff !important;
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
                25px
                28px
                88px
                28px;

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
           ICON BOX
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


        .question-icon {

            background:
                #eef2ff;

            color:
                #4f46e5;
        }


        .report-icon {

            background:
                #ecfdf5;

            color:
                #059669;
        }


        .evaluation-icon {

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
           DASHBOARD BUTTON POSITION
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


        /* =====================================================
           DASHBOARD BUTTON
        ===================================================== */

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
           COURSE SELECTION
        ===================================================== */

        .course-selection-heading {
            margin: 4px 0 12px 0;
            padding: 0 4px;
        }

        .course-selection-title {
            color: #0f172a;
            font-size: 18px;
            font-weight: 750;
            letter-spacing: -0.25px;
            margin-bottom: 4px;
        }

        .course-selection-description {
            color: #64748b;
            font-size: 13px;
            line-height: 1.5;
        }

        div[data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid #dbe3ee !important;
            border-radius: 12px !important;
            min-height: 46px !important;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.045) !important;
        }

        div[data-baseweb="select"] > div:hover {
            border-color: #c7d2fe !important;
        }

        div[data-baseweb="select"] input {
            color: #0f172a !important;
        }

        div[data-baseweb="select"] span {
            color: #334155 !important;
        }

        div[data-baseweb="popover"],
        ul[role="listbox"] {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
        }

        ul[role="listbox"] li {
            color: #334155 !important;
        }

        ul[role="listbox"] li:hover {
            background: #eef2ff !important;
            color: #4f46e5 !important;
        }


        /* =====================================================
           RESPONSIVE
        ===================================================== */

        @media (max-width: 900px) {

            html,
            body,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"],
            [data-testid="stMainBlockContainer"],
            .stApp {

                height:
                    auto !important;

                max-height:
                    none !important;

                overflow:
                    auto !important;
            }


            .block-container {

                padding-top:
                    7vh !important;

                padding-left:
                    20px !important;

                padding-right:
                    20px !important;
            }


            .welcome-section {

                margin-bottom:
                    30px;
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
                    28px
                    25px
                    100px
                    25px;
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


    # =====================================================
    # LOGOUT
    # =====================================================

    if st.button(
        "Logout",
        key="eduai_logout_button",
    ):

        st.session_state.eduai_authenticated = False

        st.session_state.eduai_login_error = None

        st.session_state.eduai_access_token = ""

        st.session_state.eduai_user_id = None

        st.session_state.eduai_user_name = ""

        st.session_state.eduai_user_role = ""

        st.rerun()


    # =====================================================
    # WELCOME MESSAGE
    # =====================================================

    st.html(
        """
        <div class="welcome-section">

            <div class="welcome-eyebrow">
                EDUAI DASHBOARD
            </div>

            <div class="welcome-title">
                Welcome to EduAI
            </div>

            <div class="welcome-description">
                Select a module below to create assessments,
                generate reports, or evaluate student assignments
                with AI-powered tools.
            </div>

        </div>
        """
    )


    # =====================================================
    # ASSIGNED COURSE SELECTION
    # =====================================================

    # IMPORTANT:
    # Do NOT use eduai_user_id here. The login user ID is the RBAC
    # identity and should not be manually passed in the URL.
    # The backend resolves the authenticated instructor from the
    # Bearer token through /instructor/me/courses.
    assigned_courses = []
    course_load_error = None

    access_token = (
        st.session_state.get("eduai_access_token")
        or st.session_state.get("access_token")
        or ""
    )

    if access_token:
        try:
            course_response = requests.get(
                f"{EDUAI_AUTH_API_URL}/instructor/me/courses",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                timeout=10,
            )

            if course_response.status_code == 200:
                payload = course_response.json()
                assigned_courses = payload.get("courses", [])
            elif course_response.status_code in (401, 403):
                course_load_error = (
                    "Your instructor session is no longer valid. "
                    "Please log in again."
                )
            else:
                try:
                    course_load_error = course_response.json().get(
                        "detail",
                        "Unable to load assigned courses.",
                    )
                except Exception:
                    course_load_error = "Unable to load assigned courses."

        except requests.exceptions.ConnectionError:
            course_load_error = (
                "Can't reach the EduAI backend. "
                "Start the FastAPI server first."
            )
        except requests.exceptions.Timeout:
            course_load_error = "Course loading request timed out."
        except requests.exceptions.RequestException:
            course_load_error = "Unable to load assigned courses."
    else:
        course_load_error = (
            "Your instructor session is missing. Please log in again."
        )


    st.html(
        """
        <div class="course-selection-heading">
            <div class="course-selection-title">
                Select Your Course
            </div>
            <div class="course-selection-description">
                Choose a course assigned to you by the administrator.
            </div>
        </div>
        """
    )

    if course_load_error:
        st.error(course_load_error)
        assigned_courses = []

    if assigned_courses:

        course_options = {
            f"{course.get('name', 'Untitled Course')}": course.get("id")
            for course in assigned_courses
        }

        course_names = list(course_options.keys())

        # Keep the course selector unselected by default.
        # A course is only stored after the instructor explicitly chooses one.
        select_options = ["None"] + course_names

        current_value = "None"
        if st.session_state.selected_course_id in course_options.values():
            selected_id = st.session_state.selected_course_id
            selected_name = next(
                (name for name, course_id in course_options.items()
                 if course_id == selected_id),
                None,
            )
            if selected_name:
                current_value = selected_name

        selected_course_name = st.selectbox(
            "Course",
            select_options,
            index=select_options.index(current_value),
            key="eduai_course_selector",
            label_visibility="collapsed",
        )

        if selected_course_name == "None":
            st.session_state.selected_course_id = None
        else:
            st.session_state.selected_course_id = course_options[
                selected_course_name
            ]

    else:

        st.info(
            "No courses have been assigned to you yet. "
            "Ask the administrator to assign a course."
        )


    # =====================================================
    # DASHBOARD COLUMNS
    # =====================================================

    col1, col2, col3 = st.columns(
        3,
        gap="large",
    )


    # =====================================================
    # QUESTION GENERATION
    # =====================================================

    with col1:

        st.html(
            """
            <div class="edu-card">

                <div class="edu-icon question-icon">
                    ✦
                </div>

                <div class="edu-title">
                    Question Generation
                </div>

                <div class="edu-description">
                    Create AI-powered assessment questions
                    based on topics, difficulty levels and
                    question types.
                </div>

            </div>
            """
        )


        if st.button(
            "Question Generation  →",
            key="question_generation",
            use_container_width=True,
        ):

            st.switch_page(
                question_generation_page
            )


    # =====================================================
    # REPORT GENERATION
    # =====================================================

    with col3:

        st.html(
            """
            <div class="edu-card">

                <div class="edu-icon report-icon">
                    ▤
                </div>

                <div class="edu-title">
                    Report Generation
                </div>

                <div class="edu-description">
                    Generate professional academic and
                    performance reports from assessment
                    and evaluation data.
                </div>

            </div>
            """
        )


        if st.button(
            "Report Generation  →",
            key="report_generation",
            use_container_width=True,
        ):

            st.switch_page(
                report_generation_page
            )


    # =====================================================
    # AI ASSIGNMENT EVALUATION
    # =====================================================

    with col2:

        st.html(
            """
            <div class="edu-card">

                <div class="edu-icon evaluation-icon">
                    ✓
                </div>

                <div class="edu-title">
                    AI Assignment Evaluation
                </div>

                <div class="edu-description">
                    Evaluate student assignments intelligently
                    using AI and structured assessment rubrics.
                </div>

            </div>
            """
        )


        if st.button(
            "AI Assignment Evaluation  →",
            key="assignment_evaluation",
            use_container_width=True,
        ):

            st.switch_page(
                assignment_evaluation_page
            )

dashboard_page()