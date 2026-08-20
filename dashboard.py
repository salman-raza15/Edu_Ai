import streamlit as st

st.set_page_config(
    page_title="EduAI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "eduai_authenticated" not in st.session_state:
    st.session_state.eduai_authenticated = False

login_page = st.Page(
    "pages/login.py",
    title="Login",
    default=not st.session_state.eduai_authenticated,
)

admin_dashboard_page = st.Page(
    "pages/admin_dashboard.py",
    title="Admin Dashboard",
    url_path="admin-dashboard",
    default=(
        st.session_state.eduai_authenticated
        and str(st.session_state.get("role", "")).upper() == "ADMIN"
    ),
)

instructor_dashboard_page = st.Page(
    "pages/instructor_dashboard.py",
    title="Instructor Dashboard",
    url_path="instructor-dashboard",
    default=(
        st.session_state.eduai_authenticated
        and str(st.session_state.get("role", "")).upper() == "INSTRUCTOR"
    ),
)

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
admin_signup_page = st.Page(
    "pages/Admin_Signup.py",
    title="Admin Signup",
    url_path="admin-signup",
)

if not st.session_state.eduai_authenticated:
    navigation = st.navigation(
        [login_page, admin_signup_page],
        position="hidden",
    )
elif str(st.session_state.get("role", "")).upper() == "ADMIN":
    navigation = st.navigation(
        [admin_dashboard_page, admin_signup_page],
        position="hidden",
    )
else:
    navigation = st.navigation(
        [
            instructor_dashboard_page,
            question_generation_page,
            assignment_evaluation_page,
            report_generation_page,
        ],
        position="hidden",
    )

navigation.run()