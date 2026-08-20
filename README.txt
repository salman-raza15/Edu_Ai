EduAI Admin RBAC

1. Create .env enter your local PostgreSQL password.
2. Make sure PostgreSQL has a database named EduAI.
3. Install requirements:
   pip install -r requirements.txt

4. Start backend from the project root:
   uvicorn backend.main:app --reload

5. In another terminal start UI:
   streamlit run dashboard.py

Admin flow:
Admin Signup -> Admin Login -> Admin Dashboard
Admin can create instructors, create courses, and assign courses to instructors.

The supplied Admin UI styling is preserved.


Merged build: admin RBAC + instructor modules are now in one project. Run `streamlit run dashboard.py` and `uvicorn backend.main:app --reload` from this folder.
