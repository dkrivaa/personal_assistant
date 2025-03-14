"""
pip install:
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- streamlit
- requests
- python-dotenv
- pymupdf
"""

import streamlit as st


login_page = st.Page(
    title='Login',
    page='views/login.py',
    default=True
)

morning_expenses_page = st.Page(
    title='Morning Expenses',
    page='views/expenses.py'
)

pages = [login_page, morning_expenses_page]

pg = st.navigation(pages=pages, position='sidebar')
pg.run()






