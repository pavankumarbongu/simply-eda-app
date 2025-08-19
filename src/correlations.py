import streamlit as st
import plotly.graph_objects as go

def show_correlations(df):
    st.subheader("🔗 Correlations & Visualizations")

    # --- A) Validate Data ---
    if df is None or df.empty:
        st.warning("No data loaded yet. Load a dataset to proceed.")
        return

    # Compute numeric cols dynamically
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.warning("No numeric columns detected in the dataset.")
        return

    # --- B) Select Target Column ---
    st.markdown("### 🎯 Select Target Variable")
    target_col = st.selectbox(
        "Choose the target column",
        numeric_cols,
        index=0,
        key="target_selector"
    )

    if not target_col or target_col not in df.columns:
        st.warning("Please select a valid target column.")
        return

    # --- C) Feature-to-Target Correlations ---
    st.markdown("### 🔎 Feature-to-Target Correlations")
    try:
        corrs = df[numeric_cols].corrwith(df[target_col]).drop(target_col, errors="ignore")
        top = corrs.sort_values(key=abs, ascending=False)
        if top.empty:
            st.info("No features meet the selected correlation threshold.")
        else:
            st.dataframe(top.to_frame("Correlation with Target"))
    except Exception as e:
        st.error(f"Error computing correlations: {e}")

    # --- D) Scatter Plot ---
    st.markdown("---")
    st.markdown("### 📈 Scatter Plot: Feature vs Target")
    feat_options = [c for c in numeric_cols if c != target_col]
    if not feat_options:
        st.info("Not enough numeric features (besides the target) to plot.")
    else:
        feat = st.selectbox("Select feature", feat_options, key="scatter_feat_sel")
        fig_scatter = go.Figure(go.Scatter(x=df[feat], y=df[target_col], mode="markers"))
        fig_scatter.update_layout(
            title=f"{feat} vs {target_col}",
            xaxis_title=feat,
            yaxis_title=target_col
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # --- E) Selected Corr Table ---
    st.markdown("---")
    st.markdown("### 🧮 Selected Features vs Target Correlation Table")

    # Auto-pick top 3 correlated features
    if feat_options:
        corrs_sorted = df[feat_options].corrwith(df[target_col]).abs().sort_values(ascending=False)
        default_corr_features = corrs_sorted.head(min(3, len(corrs_sorted))).index.tolist()
    else:
        default_corr_features = []

    sel = st.multiselect(
        "Select features",
        feat_options,
        default=default_corr_features,
        key="selected_corr_features",
    )
    if sel:
        try:
            sc = df[sel].corrwith(df[target_col]).sort_values(key=abs, ascending=False)
            st.dataframe(sc.to_frame(f"Correlation with {target_col}"))
        except Exception as e:
            st.error(f"Error computing selected correlations: {e}")
    else:
        st.info("Pick one or more features to see correlations with the target.")

    # --- F) Heatmap ---
    st.markdown("---")
    st.markdown("### 🌡️ Correlation Heatmap")
    sel_heat = st.multiselect(
        "Select features for heatmap",
        numeric_cols,
        default=numeric_cols[: min(5, len(numeric_cols))],
        key="heatmap_features",
    )
    if len(sel_heat) >= 2:
        try:
            mat = df[sel_heat].corr().round(2)
            fig_heat = go.Figure(
                go.Heatmap(
                    z=mat.values, x=sel_heat, y=sel_heat,
                    colorscale="RdBu", zmin=-1, zmax=1, colorbar_title="Correlation"
                )
            )
            fig_heat.update_layout(template="plotly_white")
            st.plotly_chart(fig_heat, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating heatmap: {e}")
    else:
        st.info("Select at least two features to render a heatmap.")
