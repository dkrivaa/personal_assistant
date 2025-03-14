import os
import streamlit as st
from dotenv import load_dotenv


# This is a simple login ###
load_dotenv()
code = os.getenv('CODE')

with st.container():
    st.subheader('Welcome')
    user_input = st.text_input('Enter site code:', value=None, type="password", placeholder='Enter code')

    if user_input is not None:
        if user_input == code:
            st.switch_page('views/expenses.py')
        else:
            st.error('The site code is incorrect')

