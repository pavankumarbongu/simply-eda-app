import os
import streamlit as st
from src.data_load import show_data_load
from src.correlations import show_correlations
from src.lift_analysis import show_lift_analysis
from src.data_summary import show_data_summary
from src.plots import show_plots

# ---------------------- Page Setup ----------------------
st.set_page_config(page_title="Correlation Analyzer", layout="wide")
st.title("📊 EDA Application")

# ---------------------- Tabs ----------------------
tabs = st.tabs([
    "Data Load",
    "Correlations",
    "Lift Analysis",
    "Data Summary",
    "Plots",
    "Raw Data",
])

# ---------------------- Data Load Tab ----------------------
with tabs[0]:
    # Only load df — target selection is now handled inside correlations & lift analysis
    df = show_data_load()

# ---------------------- Correlations Tab ----------------------
with tabs[1]:
    if df is not None:
        show_correlations(df)
    else:
        st.warning("⚠️ Load data first from the Data Load tab.")

# ---------------------- Lift Analysis Tab ----------------------
with tabs[2]:
    if df is not None:
        show_lift_analysis(df)
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
        show_plots(df)   # <-- pass df so plotting functions can use it
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
    os.system("streamlit run app.py")
