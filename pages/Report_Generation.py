import os
import sys
import base64
import hashlib

import requests
import streamlit as st

# -----------------------------------------------------------------------------
# PATH / API CONFIG
# -----------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

API_BASE = os.getenv("EDUAI_API_BASE", "http://127.0.0.1:8000")
API_PREFIX = "/report-generation"
N8N_REPORT_EMAIL_WEBHOOK_URL = "http://localhost:5678/webhook/eduai/send-report-email"

st.set_page_config(
    page_title="Report Generation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# THEME
# -----------------------------------------------------------------------------
ACCENT = "#4f46e5"
INK = "#0f172a"
MUTED = "#64748b"
BORDER = "#e2e8f0"
SUCCESS = "#059669"

st.markdown(
    f"""
<style>
header, footer, #MainMenu {{ visibility: hidden; }}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display:none !important; }}
.stApp {{ background:#f8fafc; }}
.block-container {{ max-width:1180px; padding-top:2.3rem; padding-bottom:3rem; }}

.eyebrow {{
    font-size:11px;
    font-weight:800;
    letter-spacing:1.3px;
    text-transform:uppercase;
    color:{ACCENT};
    margin-bottom:6px;
}}
.page-title {{
    font-size:30px;
    line-height:1.2;
    font-weight:800;
    letter-spacing:-.7px;
    color:{INK};
    margin-bottom:7px;
}}
.page-subtitle {{
    font-size:14px;
    line-height:1.65;
    color:{MUTED};
    max-width:760px;
    margin-bottom:14px;
}}
.header-rule {{
    border:0;
    border-top:1px solid {BORDER};
    margin:0 0 1.2rem 0;
}}
.upload-shell {{
    background:#fff;
    border:1px solid {BORDER};
    border-radius:18px;
    padding:24px;
    box-shadow:0 10px 28px rgba(15,23,42,.04);
}}
.helper-box {{
    background:#eef2ff;
    border:1px solid #dbe4ff;
    color:#4338ca;
    border-radius:12px;
    padding:12px 14px;
    font-size:13px;
    line-height:1.6;
    margin-bottom:14px;
}}
.report-card {{
    background:#fff;
    border:1px solid {BORDER};
    border-radius:16px;
    padding:18px;
    line-height:1.7;
    color:#334155;
    box-shadow:0 8px 22px rgba(15,23,42,.04);
}}
.upload-success {{
    background:#ecfdf5;
    border:1px solid #a7f3d0;
    color:#065f46;
    border-radius:12px;
    padding:11px 13px;
    font-size:13px;
    font-weight:650;
    margin-bottom:12px;
}}
.step-title {{
    font-size:15px;
    font-weight:800;
    color:{INK};
    margin-top:5px;
    margin-bottom:6px;
}}
.step-caption {{
    font-size:12.5px;
    color:{MUTED};
    margin-bottom:10px;
}}

div[data-testid="stMetric"] {{
    background:#fff;
    border:1px solid {BORDER};
    border-radius:14px;
    padding:12px 14px;
}}
.stButton button,
.stFormSubmitButton button,
div[data-testid="stDownloadButton"] button {{
    border-radius:10px !important;
    min-height:42px;
    font-weight:650;
    border:1px solid #dbe3ee;
}}
.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {{
    background:{ACCENT} !important;
    color:#fff !important;
    border-color:{ACCENT} !important;
}}
[data-baseweb="select"] > div,
.stTextInput input,
.stTextArea textarea {{
    border-radius:10px !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    background:#fff;
    border:1px dashed #cbd5e1;
    border-radius:16px;
}}

/* =====================================================
   GENERIC MODAL SIZE — same family as Question Generation
===================================================== */
div[data-testid="stDialog"] {{
    padding:12px !important;
    overflow:hidden !important;
}}

div[data-testid="stDialog"] div[role="dialog"] {{
    width:min(1120px, 92vw) !important;
    max-width:92vw !important;
    height:auto !important;
    max-height:88vh !important;
    margin:auto !important;
    border-radius:18px !important;
    overflow:hidden !important;
    box-shadow:0 24px 70px rgba(15,23,42,.20) !important;
}}

/* =====================================================
   REPORT MODAL SCROLL AREA
   Same pattern used by Question Generation / Evaluation:
   the dialog frame stays fixed and this keyed container scrolls.
===================================================== */
.st-key-report_generation_modal_scroll {{
    height:72vh !important;
    max-height:72vh !important;
    overflow-y:scroll !important;
    overflow-x:hidden !important;
    padding-right:10px !important;
    scrollbar-width:thin;
    scrollbar-color:#94a3b8 #f8fafc;
    scrollbar-gutter:stable;
}}

.st-key-report_generation_modal_scroll::-webkit-scrollbar {{
    width:10px;
}}

.st-key-report_generation_modal_scroll::-webkit-scrollbar-track {{
    background:#f8fafc;
    border-radius:999px;
}}

.st-key-report_generation_modal_scroll::-webkit-scrollbar-thumb {{
    background:#94a3b8;
    border-radius:999px;
    border:2px solid #f8fafc;
}}

.st-key-report_generation_modal_scroll::-webkit-scrollbar-thumb:hover {{
    background:#64748b;
}}

@media (max-height:800px) {{
    .st-key-report_generation_modal_scroll {{
        height:68vh !important;
        max-height:68vh !important;
    }}
}}

@media (max-width:850px) {{
    .st-key-report_generation_modal_scroll {{
        height:74vh !important;
        max-height:74vh !important;
    }}
}}

/* =====================================================
   GENERIC LOADING PANEL — matches Question Generation
===================================================== */
.loading-card {{
    background:linear-gradient(135deg,#ffffff,#f7f8ff);
    border:1px solid #c7d2fe;
    border-radius:17px;
    padding:27px;
    margin:10px 0;
    box-shadow:0 10px 30px rgba(79,70,229,.08);
}}
.loading-title {{
    color:#0f172a;
    font-size:18px;
    font-weight:760;
    margin-bottom:8px;
}}
.loading-text {{
    color:#64748b;
    font-size:13.5px;
    line-height:1.65;
    margin-bottom:21px;
}}
.loading-track {{
    position:relative;
    width:100%;
    height:7px;
    background:#e8eaf5;
    border-radius:999px;
    overflow:hidden;
}}
.loading-bar {{
    position:absolute;
    top:0;
    left:-40%;
    width:38%;
    height:100%;
    background:linear-gradient(90deg,#4f46e5,#6366f1,#818cf8);
    border-radius:999px;
    animation:modal-loading 1.2s ease-in-out infinite;
}}
@keyframes modal-loading {{
    0% {{ left:-40%; }}
    50% {{ left:45%; }}
    100% {{ left:105%; }}
}}
.loading-note {{
    color:#94a3b8;
    font-size:12px;
    margin-top:13px;
}}

@media (max-width:850px) {{
    div[data-testid="stDialog"] div[role="dialog"] {{
        width:96vw !important;
        max-width:96vw !important;
        max-height:90vh !important;
        border-radius:14px !important;
    }}
}}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# API HELPERS
# -----------------------------------------------------------------------------
def api_get(path, params=None):
    try:
        return requests.get(
            f"{API_BASE}{API_PREFIX}{path}",
            params=params,
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend. Make sure the EduAI backend is running.")
        st.stop()


def api_post(path, json_body=None, params=None):
    try:
        return requests.post(
            f"{API_BASE}{API_PREFIX}{path}",
            json=json_body,
            params=params,
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend. Make sure the EduAI backend is running.")
        st.stop()


def api_put(path, json_body):
    try:
        return requests.put(
            f"{API_BASE}{API_PREFIX}{path}",
            json=json_body,
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend. Make sure the EduAI backend is running.")
        st.stop()


def api_post_file_bytes(path, filename, file_bytes):
    try:
        files = {"file": (filename, file_bytes)}
        return requests.post(
            f"{API_BASE}{API_PREFIX}{path}",
            files=files,
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend. Make sure the EduAI backend is running.")
        st.stop()


def response_detail(response, fallback="Something went wrong."):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("detail") or data.get("message") or fallback
    except Exception:
        pass
    return response.text or fallback


# -----------------------------------------------------------------------------
# REPORT RENDERER
# -----------------------------------------------------------------------------
def render_report(result: dict):
    analytics = result.get("analytics", {}) or {}

    if "error" in analytics or "error" in result:
        st.warning(analytics.get("error") or result.get("error"))
        return

    scope = str(result.get("scope", "Report")).capitalize()
    scope_id = result.get("scope_id", "-")

    st.markdown(
        f"<div style='font-size:1.05rem;font-weight:800;color:{INK};margin:.25rem 0 .6rem 0;'>"
        f"{scope}: {scope_id}</div>",
        unsafe_allow_html=True,
    )

    if result.get("cache_key"):
        st.caption(
            f"Report ID: `{result['cache_key']}` · "
            f"Type: {result.get('report_type', '-')}"
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average", f"{analytics.get('average_percentage', '-')}%")
    c2.metric("Highest", f"{analytics.get('highest_percentage', '-')}%")
    c3.metric("Lowest", f"{analytics.get('lowest_percentage', '-')}%")
    c4.metric("Pass Rate", f"{analytics.get('pass_rate', '-')}%")

    st.markdown(
        f"<div class='report-card'>{result.get('narrative_text', '')}</div>",
        unsafe_allow_html=True,
    )

    rubric = analytics.get("rubric_analysis")
    if rubric:
        st.markdown("**Rubric-wise Average (%)**")
        st.bar_chart(rubric, color=ACCENT)

    breakdown = analytics.get("student_breakdown")
    if breakdown:
        with st.expander("Student-wise breakdown"):
            st.dataframe(breakdown, use_container_width=True)


# -----------------------------------------------------------------------------
# OPTION HELPERS
# -----------------------------------------------------------------------------
def get_scope_options(scope: str):
    r = api_get("/data/options")
    if r.status_code != 200:
        return [], {}, response_detail(r, "Could not load report options.")

    opts = r.json() or {}
    id_to_label = {}

    if scope == "individual":
        items = opts.get("individual", []) or []
        values = [str(item.get("student_id")) for item in items]
        id_to_label = {
            str(item.get("student_id")): (
                f"{item.get('student_id')} — {item.get('student_name', 'Student')}"
            )
            for item in items
        }
        return values, id_to_label, None

    if scope == "course":
        return opts.get("course", []) or [], {}, None

    if scope == "cohort":
        return opts.get("cohort", []) or [], {}, None

    if scope == "assignment":
        return opts.get("assignment", []) or [], {}, None

    return [], {}, None


# -----------------------------------------------------------------------------
# SESSION HELPERS
# -----------------------------------------------------------------------------
def file_token(filename: str, file_bytes: bytes) -> str:
    digest = hashlib.sha1(file_bytes).hexdigest()[:14]
    return f"{filename}:{len(file_bytes)}:{digest}"


def clear_generated_report_state():
    keys = [
        "report_result",
        "report_preview_visible",
        "report_edit_visible",
        "report_edit_version",
        "report_download_data",
        "report_download_ext",
        "report_download_mime",
        "report_download_filename",
        "report_email_visible",
        "report_email_recipient",
        "report_email_sent",
    ]
    for key in keys:
        st.session_state.pop(key, None)


# -----------------------------------------------------------------------------
# GENERIC EDUAI LOADER
# Uses the same visual language as Question Generation / Assignment Evaluation.
# -----------------------------------------------------------------------------
def show_generic_loader(title: str, message: str, note: str):
    area = st.empty()
    area.html(
        f"""
        <div class="loading-card">
            <div class="loading-title">{title}</div>
            <div class="loading-text">{message}</div>
            <div class="loading-track">
                <div class="loading-bar"></div>
            </div>
            <div class="loading-note">{note}</div>
        </div>
        """
    )
    return area


# -----------------------------------------------------------------------------
# MAIN MODAL WORKFLOW
# -----------------------------------------------------------------------------
@st.dialog("Send Report via Email", width="small")
def send_report_email_modal():
    st.markdown(
        "Enter the recipient email address. The prepared PDF will be sent through the configured n8n workflow."
    )

    recipient_email = st.text_input(
        "Recipient email",
        placeholder="recipient@example.com",
        key="report_email_recipient_modal",
    )

    send_col, cancel_col = st.columns(2)

    if send_col.button(
        "Send Email",
        type="primary",
        use_container_width=True,
        key="report_email_modal_send",
    ):
        email = recipient_email.strip()

        if not email:
            st.warning("Please enter a recipient email address.")
            return

        result = st.session_state.get("report_result") or {}
        cache_key = result.get("cache_key")
        pdf_data = st.session_state.get("report_download_data")
        filename_to_send = st.session_state.get(
            "report_download_filename",
            f"report_{cache_key}.pdf" if cache_key else "report.pdf",
        )

        if not cache_key:
            st.error("This report has no Report ID, so it cannot be emailed.")
            return
        if not pdf_data:
            st.error("Please prepare the PDF download first.")
            return
        if st.session_state.get("report_download_ext") != "pdf":
            st.error("Please prepare the report as a PDF before sending it by email.")
            return

        data = {
            "recipient_email": email,
            "report_id": cache_key,
            "filename": filename_to_send,
            "report_name": filename_to_send,
        }
        files = {
            "file": (filename_to_send, pdf_data, "application/pdf")
        }

        loading_area = show_generic_loader(
            "Sending report via email",
            "EduAI is sending the prepared PDF through the configured n8n email workflow.",
            "Please keep this window open until the email request finishes.",
        )
        try:
            email_response = requests.post(
                N8N_REPORT_EMAIL_WEBHOOK_URL,
                data=data,
                files=files,
                timeout=60,
            )
        except requests.RequestException as exc:
            loading_area.empty()
            st.error(
                "Could not reach the n8n webhook. "
                f"Make sure n8n is running at {N8N_REPORT_EMAIL_WEBHOOK_URL}. "
                f"Details: {exc}"
            )
            return

        loading_area.empty()
        if 200 <= email_response.status_code < 300:
            try:
                response_json = email_response.json()
                message = response_json.get("message", "Report sent successfully.")
            except Exception:
                message = "Report sent successfully."

            st.session_state["report_email_success_message"] = message
            st.session_state["report_email_modal_open"] = False
            st.rerun()
        else:
            try:
                detail = email_response.json().get("detail", email_response.text)
            except Exception:
                detail = email_response.text or "Could not send the report."
            st.error(f"n8n returned HTTP {email_response.status_code}: {detail}")

    if cancel_col.button(
        "Cancel",
        use_container_width=True,
        key="report_email_modal_cancel",
    ):
        st.session_state["report_email_modal_open"] = False
        st.rerun()


@st.dialog("Generate Performance Report", width="large")
def report_workflow_dialog(filename: str, file_bytes, token: str):
    with st.container(key="report_generation_modal_scroll"):
        st.markdown(
            "<div class='step-caption'>Your file is processed first. Everything else "
            "— report setup, generation, preview, editing and download — stays inside "
            "this window.</div>",
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # STEP 1: UPLOAD / PARSE ONLY ONCE PER FILE
        # ------------------------------------------------------------------
        if st.session_state.get("processed_report_file_token") != token:
            clear_generated_report_state()

            if file_bytes is None:
                loading_area = show_generic_loader(
                    "Loading AI Evaluation results",
                    "EduAI is loading the latest ZIP evaluation results saved in the database.",
                    "The saved evaluation output is being prepared directly for reporting.",
                )
                status_response = api_get("/data/status")
                options_response = api_get("/data/options")
                loading_area.empty()

                if status_response.status_code != 200:
                    st.error(response_detail(status_response, "Could not load AI Evaluation results."))
                    return

                status_info = status_response.json()
                options = options_response.json() if options_response.status_code == 200 else {}
                st.session_state["report_upload_info"] = {
                    "message": "Latest AI Evaluation results loaded directly from the database.",
                    "rows": status_info.get("rows", 0),
                    "students": len(options.get("individual", []) or []),
                    "courses": options.get("course", []) or [],
                    "cohorts": options.get("cohort", []) or [],
                    "warnings": [],
                }
            else:
                loading_area = show_generic_loader(
                    "Processing evaluation results",
                    "Your uploaded file is being parsed, validated and prepared as the active dataset for report generation.",
                    "Processing is in progress. Please keep this window open.",
                )
                upload_response = api_post_file_bytes(
                    "/data/upload",
                    filename,
                    file_bytes,
                )
                loading_area.empty()

                if upload_response.status_code != 200:
                    st.error(response_detail(upload_response, "Could not upload the file."))
                    if st.button("Close", use_container_width=True, key="close_failed_upload"):
                        st.session_state["report_dialog_closed_for"] = token
                        st.rerun()
                    return

                st.session_state["report_upload_info"] = upload_response.json()

            st.session_state["processed_report_file_token"] = token

        upload_info = st.session_state.get("report_upload_info", {}) or {}

        st.markdown(
            f"<div class='upload-success'>✓ {upload_info.get('message', 'File loaded successfully.')}</div>",
            unsafe_allow_html=True,
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Rows", upload_info.get("rows", 0))
        m2.metric("Students", upload_info.get("students", 0))
        m3.metric("Courses", len(upload_info.get("courses", []) or []))

        warnings = upload_info.get("warnings", []) or []
        if warnings:
            with st.expander(f"{len(warnings)} data quality warning(s)"):
                for warning in warnings:
                    st.write(f"- {warning}")

        st.divider()

        # ------------------------------------------------------------------
        # STEP 2: REPORT SETTINGS — NO RADIO BUTTONS
        # ------------------------------------------------------------------
        st.markdown("<div class='step-title'>Report settings</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='step-caption'>Choose what the report should summarize.</div>",
            unsafe_allow_html=True,
        )

        left, right = st.columns(2)

        with left:
            scope = st.selectbox(
                "Report scope",
                ["course", "cohort", "assignment", "individual"],
                key="modal_report_scope",
                format_func=lambda value: value.capitalize(),
            )

        scope_options, id_to_label, option_error = get_scope_options(scope)

        with right:
            if scope_options:
                scope_id = st.selectbox(
                    "Report for",
                    scope_options,
                    format_func=lambda value: id_to_label.get(str(value), str(value)),
                    key=f"modal_scope_id_{scope}",
                )
            else:
                scope_id = None
                st.selectbox(
                    "Report for",
                    ["No options available"],
                    disabled=True,
                    key=f"modal_scope_id_empty_{scope}",
                )

        if option_error:
            st.warning(option_error)

        report_type = st.selectbox(
            "Report type",
            ["course", "cohort", "assignment", "individual", "weekly", "monthly", "custom"],
            key="modal_report_type",
            format_func=lambda value: value.capitalize(),
        )

        with st.expander("Optional date range"):
            d1, d2 = st.columns(2)
            date_from = d1.text_input(
                "Date from",
                placeholder="YYYY-MM-DD",
                key="modal_date_from",
            )
            date_to = d2.text_input(
                "Date to",
                placeholder="YYYY-MM-DD",
                key="modal_date_to",
            )

        # ------------------------------------------------------------------
        # STEP 3: GENERATE WITH LOADER
        # ------------------------------------------------------------------
        if st.button(
            "Generate Report",
            type="primary",
            use_container_width=True,
            key="modal_generate_report",
        ):
            if not scope_id:
                st.warning("No matching data is available for the selected report scope.")
            else:
                body = {
                    "scope": scope,
                    "scope_id": scope_id,
                    "report_type": report_type,
                    "date_from": date_from or None,
                    "date_to": date_to or None,
                    # Save automatically so View/Edit/Download all have a cache_key.
                    "save": True,
                }

                loading_area = show_generic_loader(
                    "Generating your performance report",
                    "EduAI is analyzing the selected evaluation data, calculating performance metrics and preparing the report narrative.",
                    "Report generation is in progress. Please keep this window open.",
                )
                report_response = api_post("/reports", json_body=body)
                loading_area.empty()

                if report_response.status_code == 200:
                    result = report_response.json()
                    st.session_state["report_result"] = result
                    st.session_state["report_preview_visible"] = False
                    st.session_state["report_edit_visible"] = False
                    st.session_state["report_edit_version"] = st.session_state.get("report_edit_version", 0) + 1

                    for key in (
                        "report_download_data",
                        "report_download_ext",
                        "report_download_mime",
                        "report_download_filename",
                    ):
                        st.session_state.pop(key, None)

                    st.success("Report generated successfully.")
                else:
                    st.error(response_detail(report_response, "Could not generate the report."))

        result = st.session_state.get("report_result")

        # ------------------------------------------------------------------
        # STEP 4: REPORT FORMAT (MATCH QUESTION GENERATION PAGE FORMAT UI)
        # ------------------------------------------------------------------
        if result:
            st.divider()
            st.markdown("<div class='step-title'>Report format</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='step-caption'>Choose how the final report should be formatted before previewing or editing it.</div>",
                unsafe_allow_html=True,
            )

            report_format_choice = st.radio(
                "Report format",
                [
                    "Default EduAI Format",
                    "Upload Letterhead",
                ],
                horizontal=True,
                label_visibility="collapsed",
                key="modal_report_format_choice",
            )

            custom_letterhead = None

            if report_format_choice == "Upload Letterhead":
                custom_letterhead = st.file_uploader(
                    "Upload Letterhead",
                    type=["pdf", "png", "jpg", "jpeg"],
                    key="modal_custom_letterhead",
                    help="Supported formats: PDF, PNG, JPG and JPEG.",
                )
                if custom_letterhead is not None:
                    st.success(f"Letterhead selected: {custom_letterhead.name}")


            # ------------------------------------------------------------------
            # STEP 5: PREVIEW / EDIT
            # ------------------------------------------------------------------
            st.markdown("<div class='step-title'>Report actions</div>", unsafe_allow_html=True)

            action1, action2 = st.columns(2)

            if action1.button(
                "Preview Report",
                use_container_width=True,
                key="modal_preview_report",
            ):
                st.session_state["report_preview_visible"] = True
                st.session_state["report_edit_visible"] = False

            if action2.button(
                "Edit Report",
                use_container_width=True,
                key="modal_edit_report",
            ):
                st.session_state["report_edit_visible"] = True
                st.session_state["report_preview_visible"] = False

            if st.session_state.get("report_preview_visible", False):
                st.markdown("<div class='step-title'>Preview</div>", unsafe_allow_html=True)
                render_report(st.session_state["report_result"])

            # --------------------------------------------------------------
            # STEP 6: EDIT NARRATIVE
            # --------------------------------------------------------------
            if st.session_state.get("report_edit_visible", False):
                st.markdown("<div class='step-title'>Edit report summary</div>", unsafe_allow_html=True)

                current_cache_key = st.session_state["report_result"].get("cache_key", "new")
                edit_version = st.session_state.get("report_edit_version", 0)
                edited_text = st.text_area(
                    "Summary text",
                    value=st.session_state["report_result"].get("narrative_text", ""),
                    height=180,
                    key=f"report_edit_text_{current_cache_key}_{edit_version}",
                    label_visibility="collapsed",
                )

                save_col, cancel_col = st.columns(2)

                if save_col.button(
                    "Save Changes",
                    type="primary",
                    use_container_width=True,
                    key="modal_save_report_changes",
                ):
                    cache_key = st.session_state["report_result"].get("cache_key")

                    if not cache_key:
                        st.error("This report has no Report ID, so it cannot be edited.")
                    elif not edited_text.strip():
                        st.warning("Report summary cannot be empty.")
                    else:
                        loading_area = show_generic_loader(
                            "Saving report changes",
                            "Your edited report summary is being validated and saved to the report record.",
                            "Saving changes. Please keep this window open.",
                        )
                        update_response = api_put(
                            f"/reports/{cache_key}",
                            {"narrative_text": edited_text.strip()},
                        )
                        loading_area.empty()

                        if update_response.status_code == 200:
                            st.session_state["report_result"] = update_response.json()
                            st.session_state["report_edit_version"] = (
                                st.session_state.get("report_edit_version", 0) + 1
                            )
                            st.session_state["report_edit_visible"] = False
                            st.success("Report updated successfully.")
                        else:
                            st.error(response_detail(update_response, "Could not update the report."))

                if cancel_col.button(
                    "Cancel Edit",
                    use_container_width=True,
                    key="modal_cancel_report_edit",
                ):
                    st.session_state["report_edit_visible"] = False
                    st.session_state["report_edit_version"] = (
                        st.session_state.get("report_edit_version", 0) + 1
                    )

            # --------------------------------------------------------------
            # STEP 7: DOWNLOAD
            # The selected export is prepared automatically. This keeps the
            # UI compact and removes the extra "Prepare Download" step.
            # --------------------------------------------------------------
            st.divider()
            st.markdown("<div class='step-title'>Download report</div>", unsafe_allow_html=True)

            fmt = st.selectbox(
                "Download format",
                ["pdf", "excel", "csv"],
                key="modal_download_format",
                format_func=lambda value: "Excel (.xlsx)" if value == "excel" else value.upper(),
            )

            letterhead_mode = (
                "custom" if report_format_choice == "Upload Letterhead" else "default"
            )
            cache_key = st.session_state["report_result"].get("cache_key")

            letterhead_signature = "default"
            if letterhead_mode == "custom" and custom_letterhead is not None:
                letterhead_signature = f"{custom_letterhead.name}:{len(custom_letterhead.getvalue())}"

            download_signature = f"{cache_key}|{fmt}|{letterhead_mode}|{letterhead_signature}"

            if st.session_state.get("report_download_signature") != download_signature:
                for key in (
                    "report_download_data",
                    "report_download_ext",
                    "report_download_mime",
                    "report_download_filename",
                ):
                    st.session_state.pop(key, None)

                if not cache_key:
                    st.error("This report has no Report ID, so it cannot be downloaded.")
                elif fmt == "pdf" and letterhead_mode == "custom" and custom_letterhead is None:
                    st.info("Upload your letterhead above to enable the PDF download.")
                else:
                    loading_area = show_generic_loader(
                        f"Preparing {fmt.upper()} report",
                        "EduAI is formatting the generated report in the selected export format.",
                        "The file will be ready automatically. Please keep this window open.",
                    )

                    if fmt == "pdf":
                        payload = {"letterhead_mode": letterhead_mode}
                        if custom_letterhead is not None:
                            payload["letterhead_name"] = custom_letterhead.name
                            payload["letterhead_data"] = base64.b64encode(
                                custom_letterhead.getvalue()
                            ).decode("utf-8")

                        download_response = api_post(
                            f"/reports/{cache_key}/download",
                            json_body=payload,
                            params={"format": "pdf"},
                        )
                    else:
                        download_response = api_get(
                            f"/reports/{cache_key}/download",
                            params={"format": fmt},
                        )

                    loading_area.empty()

                    if download_response.status_code == 200:
                        mime_map = {
                            "pdf": "application/pdf",
                            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "csv": "text/csv",
                        }
                        ext_map = {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}
                        ext = ext_map[fmt]

                        st.session_state["report_download_data"] = download_response.content
                        st.session_state["report_download_ext"] = ext
                        st.session_state["report_download_mime"] = mime_map[fmt]
                        st.session_state["report_download_filename"] = f"report_{cache_key}.{ext}"
                        st.session_state["report_download_signature"] = download_signature
                    else:
                        st.error(response_detail(download_response, "Could not prepare the download."))

            if st.session_state.get("report_download_data") is not None:
                prepared_ext = st.session_state.get("report_download_ext", "")

                if prepared_ext == "pdf":
                    download_col, email_col = st.columns(2)
                    with download_col:
                        st.download_button(
                            "Download PDF",
                            data=st.session_state["report_download_data"],
                            file_name=st.session_state["report_download_filename"],
                            mime=st.session_state["report_download_mime"],
                            use_container_width=True,
                            key="modal_download_report_file",
                        )

                    with email_col:
                        if st.button(
                            "Send Report via Email",
                            use_container_width=True,
                            key="modal_open_report_email",
                        ):
                            st.session_state["report_email_modal_open"] = True
                            st.rerun()

                    if st.session_state.get("report_email_success_message"):
                        st.success(st.session_state.pop("report_email_success_message"))
                else:
                    st.download_button(
                        f"Download {prepared_ext.upper()}",
                        data=st.session_state["report_download_data"],
                        file_name=st.session_state["report_download_filename"],
                        mime=st.session_state["report_download_mime"],
                        use_container_width=True,
                        key="modal_download_report_file",
                    )

        st.divider()
        if st.button(
            "Close",
            use_container_width=True,
            key="modal_close_report_workflow",
        ):
            st.session_state["report_dialog_closed_for"] = token
            st.rerun()


# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
back_col, title_col = st.columns([0.6, 9.4], gap="small", vertical_alignment="top")

with back_col:
    if st.button(
        "‹",
        key="report_back_dashboard",
        help="Back to dashboard",
    ):
        st.switch_page("pages/instructor_dashboard.py")

with title_col:
    st.markdown("<div class='eyebrow'>EduAI Analytics</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>Report Generation</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='page-subtitle'>Upload your evaluation results once. "
        "Report generation, preview, editing and download continue in one focused workflow.</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr class='header-rule'>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# REPORT INPUT
# Saved AI Evaluation XLSX batches are the primary report source. The selector
# is always visible so the user can choose any previously saved evaluation batch.
# Manual upload remains available for external/older files.
# -----------------------------------------------------------------------------
st.markdown("<div class='eyebrow'>Start Here</div>", unsafe_allow_html=True)
st.markdown(
    "<div style='font-size:20px;font-weight:800;color:#0f172a;margin-bottom:5px;'>"
    "Report Data</div>",
    unsafe_allow_html=True,
)

# Load every saved AI Evaluation batch directly from the database-backed API.
# This must not depend on whichever dataset happens to be active right now.
try:
    batches_response = requests.get(
        f"{API_BASE}{API_PREFIX}/data/evaluation-batches",
        timeout=10,
    )
    if batches_response.status_code == 200:
        evaluation_batches = batches_response.json()
        if not isinstance(evaluation_batches, list):
            evaluation_batches = []
    else:
        evaluation_batches = []
except requests.RequestException:
    evaluation_batches = []

# Read status only to preselect the currently active batch when possible.
try:
    status = requests.get(f"{API_BASE}{API_PREFIX}/data/status", timeout=10)
except requests.RequestException:
    status = None
status_info = status.json() if status is not None and status.status_code == 200 else {}
active_batch_id = status_info.get("batch_id")

if evaluation_batches:
    batch_by_id = {item["batch_id"]: item for item in evaluation_batches}
    batch_ids = list(batch_by_id.keys())
    default_index = batch_ids.index(active_batch_id) if active_batch_id in batch_ids else 0

    def _batch_label(batch_id):
        item = batch_by_id[batch_id]
        filename = item.get("xlsx_filename") or f"Evaluation Batch {batch_id}"
        course = item.get("course_id") or "Course not assigned"
        assignment = item.get("assignment_id") or "Assignment not assigned"
        rows = item.get("rows", 0)
        created = str(item.get("created_at") or "").replace("T", " ")[:16]
        label = f"{filename}  •  {course}  •  {assignment}  •  {rows} row(s)"
        if created:
            label += f"  •  {created}"
        return label

    selected_batch_id = st.selectbox(
        "Select Saved Evaluation XLSX",
        batch_ids,
        index=default_index,
        format_func=_batch_label,
        key="report_evaluation_batch_selector",
        help="Choose one of the AI Evaluation XLSX batches that was saved to the database.",
    )
    selected_batch = batch_by_id[selected_batch_id]

    if st.button(
        "Generate Report from Selected Evaluation",
        type="primary",
        use_container_width=True,
        key="use_selected_ai_evaluation_report_data",
    ):
        try:
            activate_response = requests.post(
                f"{API_BASE}{API_PREFIX}/data/evaluation-batches/{selected_batch_id}/activate",
                timeout=20,
            )
        except requests.RequestException:
            activate_response = None

        if activate_response is not None and activate_response.status_code == 200:
            activated = activate_response.json()
            db_token = f"db:{selected_batch_id}:{activated.get('rows', 0)}"
            st.session_state["open_db_report_token"] = db_token
            st.session_state["selected_db_report_filename"] = activated.get(
                "filename",
                selected_batch.get("xlsx_filename", "AI_Evaluation_Results.xlsx"),
            )
            st.session_state.pop("report_dialog_closed_for", None)
            st.rerun()
        else:
            try:
                detail = activate_response.json().get(
                    "detail",
                    "Could not activate the selected evaluation batch.",
                )
            except Exception:
                detail = (
                    "Could not activate the selected evaluation batch. "
                    "Make sure the backend is running and the report-generation batch endpoints are available."
                )
            st.error(detail)

    st.caption(
        f"Selected XLSX: {selected_batch.get('xlsx_filename', 'AI Evaluation Results')} · "
        f"{selected_batch.get('rows', 0)} criterion row(s)"
    )
else:
    # Keep the selection control visible even when the DB has no saved batches yet.
    st.selectbox(
        "Select Saved Evaluation XLSX",
        ["No saved evaluation XLSX files available"],
        index=0,
        disabled=True,
        key="report_empty_evaluation_batch_selector",
    )
    st.button(
        "Generate Report from Selected Evaluation",
        type="primary",
        use_container_width=True,
        disabled=True,
        key="disabled_use_selected_ai_evaluation_report_data",
    )
    st.info(
        "No saved AI Evaluation batches were found in the database. "
        "In AI Assignment Evaluation, evaluate a ZIP and click 'Save Batch Marks'."
    )

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
st.caption("Or upload an external/older evaluation results file:")

uploaded_file = st.file_uploader(
    "Upload evaluation results",
    type=["csv", "pdf", "xlsx", "docx", "pptx", "zip"],
    label_visibility="collapsed",
    key="single_report_upload",
)

if uploaded_file is None:
    st.session_state.pop("last_selected_report_file_token", None)

# DB-driven modal has priority when explicitly requested.
db_token = st.session_state.get("open_db_report_token")
if db_token and st.session_state.get("report_dialog_closed_for") != db_token:
    if st.session_state.get("report_email_modal_open"):
        send_report_email_modal()
    else:
        report_workflow_dialog(
            st.session_state.get(
                "selected_db_report_filename",
                status_info.get("filename", "AI_Evaluation_Results.xlsx"),
            ),
            None,
            db_token,
        )
elif uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    token = file_token(uploaded_file.name, bytes_data)

    if st.session_state.get("last_selected_report_file_token") != token:
        st.session_state["last_selected_report_file_token"] = token
        st.session_state.pop("report_dialog_closed_for", None)
        st.session_state.pop("open_db_report_token", None)

    if st.session_state.get("report_dialog_closed_for") != token:
        if st.session_state.get("report_email_modal_open"):
            send_report_email_modal()
        else:
            report_workflow_dialog(uploaded_file.name, bytes_data, token)