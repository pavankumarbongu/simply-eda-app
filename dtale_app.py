import streamlit as st
import pandas as pd
import dtale

# Sample DataFrame
df = pd.read_csv('analysis/eda/geel_s12_data.csv')
# Start D-Tale on localhost
d = dtale.show(df, host='localhost', open_browser=False)
url = d._main_url

# Streamlit page config
st.set_page_config(layout="wide")

# Hide Streamlit default UI elements (optional)
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding: 0rem 0rem 0rem 0rem;
        }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Embed D-Tale in full-screen iframe
st.components.v1.iframe(src=url, height=1000, width=1500, scrolling=True)

if __name__ == "__main__":
    import os
    os.system("streamlit run analysis/eda/dtale_app.py")