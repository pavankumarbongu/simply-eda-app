import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def show_plots(df):
    st.subheader("📈 Interactive Data Visualizations")

    df = st.session_state.get("df")
    if df is None:
        st.warning("⚠️ No data loaded. Please load data first.")
        return

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=np.number).columns.tolist()

    plot_type = st.radio("Select Plot Type", ["Univariate", "Bivariate", "Multivariate"], horizontal=True)

    # ---------------------- UNIVARIATE ----------------------
    if plot_type == "Univariate":
        col = st.selectbox("Select a column", df.columns)
        if col:
            st.markdown(f"### 🔍 Univariate Analysis: `{col}`")

            if pd.api.types.is_numeric_dtype(df[col]):
                try:
                    # Distribution Plot
                    fig_dist = px.histogram(df, x=col, nbins=30, marginal="box", title=f"Distribution of {col}")
                    fig_dist.update_traces(marker_color="royalblue")
                    st.plotly_chart(fig_dist, use_container_width=True)
                except Exception as e:
                    st.info(f"⚠️ Could not plot distribution: {e}")

                try:
                    # Count of unique values
                    counts = df[col].value_counts().reset_index()
                    counts.columns = [col, "count"]
                    fig_count = px.bar(counts, x=col, y="count", title=f"Count of Unique Values in {col}")
                    st.plotly_chart(fig_count, use_container_width=True)
                except Exception as e:
                    st.info(f"⚠️ Could not plot count: {e}")

                # Summary
                st.markdown(f"**Summary**: Mean = {df[col].mean():.2f}, Std = {df[col].std():.2f}, Skewness = {df[col].skew():.2f}")

            else:
                try:
                    counts = df[col].value_counts().reset_index()
                    counts.columns = [col, "count"]
                    fig = px.bar(counts, x=col, y="count", title=f"Frequency of {col}", color="count", color_continuous_scale="Viridis")
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown(f"**Top Category**: {counts[col].iloc[0]} ({counts['count'].iloc[0]} occurrences)")
                except Exception as e:
                    st.info(f"⚠️ Could not plot categorical count: {e}")

    # ---------------------- BIVARIATE ----------------------
    elif plot_type == "Bivariate":
        col_x = st.selectbox("Select X-axis column", df.columns)
        col_y = st.selectbox("Select Y-axis column", [c for c in df.columns if c != col_x])

        if col_x and col_y:
            st.markdown(f"### 🔍 Bivariate Analysis: `{col_x}` vs `{col_y}`")

            if pd.api.types.is_numeric_dtype(df[col_x]) and pd.api.types.is_numeric_dtype(df[col_y]):
                try:
                    fig = px.scatter(df, x=col_x, y=col_y, trendline="ols", title=f"Scatter: {col_x} vs {col_y}")
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown(f"**Correlation**: {df[col_x].corr(df[col_y]):.2f}")
                except Exception as e:
                    st.info(f"⚠️ Could not plot scatter: {e}")
            else:
                try:
                    fig = px.box(df, x=col_x, y=col_y, points="all", title=f"Boxplot: {col_x} vs {col_y}")
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info(f"⚠️ Could not plot boxplot: {e}")

    # ---------------------- MULTIVARIATE ----------------------
    elif plot_type == "Multivariate":
        st.markdown("### 🔍 Multivariate Analysis (X, Y, and Color + Extra Hover Info)")

        col_x = st.selectbox("Select X-axis column", df.columns)
        col_y = st.selectbox("Select Y-axis column", [c for c in df.columns if c != col_x])
        color_var = st.selectbox("Select Color scale variable", [c for c in df.columns if c not in [col_x, col_y]])

        extra_hover_vars = st.multiselect(
            "Select additional variables to show on hover",
            [c for c in df.columns if c not in [col_x, col_y, color_var]],
            default=[],
        )

        if col_x and col_y and color_var:
            try:
                # Handle numeric vs categorical color mapping
                if pd.api.types.is_numeric_dtype(df[color_var]):
                    color_scale = "Viridis"
                else:
                    color_scale = None  # Let plotly handle categorical colors

                # Build hover data dict
                hover_dict = {var: True for var in [col_x, col_y, color_var] + extra_hover_vars}

                fig = px.scatter(
                    df,
                    x=col_x,
                    y=col_y,
                    color=color_var,
                    color_continuous_scale=color_scale,
                    hover_data=hover_dict,
                    title=f"Multivariate Scatter: {col_x} vs {col_y} (Color: {color_var})"
                )

                fig.update_traces(marker=dict(size=8), selector=dict(mode='markers'))
                fig.update_layout(
                    legend=dict(title=color_var),
                    hovermode="closest"
                )

                st.plotly_chart(fig, use_container_width=True)

                # Insights
                if pd.api.types.is_numeric_dtype(df[col_y]):
                    corr_text = ""
                    if pd.api.types.is_numeric_dtype(df[color_var]):
                        corr_val = df[col_y].corr(df[color_var])
                        corr_text = f" and `{color_var}` (Correlation: {corr_val:.2f})"
                    st.markdown(f"**Highlights**: Observing relation between `{col_x}` and `{col_y}`{corr_text}.")
                else:
                    st.markdown(f"**Highlights**: Patterns in `{col_y}` across `{col_x}`, grouped by `{color_var}`.")

            except Exception as e:
                st.info(f"⚠️ Could not plot multivariate: {e}")
