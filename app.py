import os
import streamlit as st
from data_load import show_data_load
from correlations import show_correlations
from lift_analysis import show_lift_analysis
from data_summary import show_data_summary
from plots import show_plots  #

# ---------------------- Page Setup ----------------------
st.set_page_config(page_title="Correlation Analyzer", layout="wide")
st.title("📊 EDA Application")

# ---------------------- Tabs ----------------------
tabs = st.tabs([
    "Data Load",
    "Correlations",
    "Lift Analysis",
    "Data Summary",
    "Plots",          # <-- NEW TAB
    "Raw Data",
])

# ---------------------- Data Load Tab ----------------------
with tabs[0]:
    df, target_col, numeric_cols, valid_default_corr_features = show_data_load()

# ---------------------- Correlations Tab ----------------------
with tabs[1]:
    if df is not None:
        show_correlations(df, numeric_cols, target_col, valid_default_corr_features)
    else:
        st.warning("⚠️ Load data first from the Data Load tab.")

# ---------------------- Lift Analysis Tab ----------------------
with tabs[2]:
    if df is not None:
        show_lift_analysis(df, target_col)
    else:
        st.warning("⚠️ Load data first from the Data Load tab.")

# ---------------------- Data Summary Tab ----------------------
with tabs[3]:
    if df is not None:
        show_data_summary(df)
    else:
        st.warning("⚠️ Load data first from the Data Load tab.")

# ---------------------- Plots Tab ----------------------
with tabs[4]:
    if df is not None:
        show_plots()
    else:
        st.warning("⚠️ Load data first from the Data Load tab.")

# ---------------------- Raw Data Tab ----------------------
with tabs[5]:
    st.subheader("🧾 Raw Data Preview")
    if df is not None:
        st.dataframe(df)
    else:
        st.warning("⚠️ Load data first from the Data Load tab.")

# ---------------------- Main Entry ----------------------
if __name__ == "__main__":
    os.system("streamlit run analysis/eda_app/app.py --server.runOnSave true")
