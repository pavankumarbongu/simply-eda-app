import streamlit as st
import numpy as np
import plotly.graph_objects as go
from sklearn.impute import SimpleImputer
import pandas as pd

@st.cache_data(show_spinner=False, persist=True)
def build_lift_reports(df, target, impute_target, target_imp, impute_feat, feat_imp):
    df_clean = df.copy()

    # Impute target if requested
    if impute_target and df_clean[target].isna().any():
        df_clean[target] = SimpleImputer(strategy=target_imp).fit_transform(df_clean[[target]]).ravel()

    # Impute numeric features if requested
    num_cols = df_clean.select_dtypes(include="number").columns.tolist()
    if impute_feat:
        feat_cols = [c for c in num_cols if c != target and df_clean[c].isna().any()]
        if feat_cols:
            df_clean[feat_cols] = SimpleImputer(strategy=feat_imp).fit_transform(df_clean[feat_cols])

    # Drop rows with missing target
    df_clean = df_clean.dropna(subset=[target])

    # Bin target
    med = df_clean[target].median()
    df_clean["target_bin"] = pd.cut(df_clean[target], [-np.inf, med, np.inf], labels=["bad", "good"])
    overall = (df_clean["target_bin"] == "good").mean()

    # Build lift tables per feature
    reports = {}
    for feat in (c for c in num_cols if c != target):
        if df_clean[feat].notna().sum() < 10:
            continue
        try:
            df_clean[f"{feat}_bin"] = pd.qcut(df_clean[feat].rank(method="first"), q=10, duplicates="drop")
            bin_df = (
                df_clean.groupby(f"{feat}_bin")["target_bin"]
                .apply(lambda x: (x == "good").mean())
                .reset_index(name="good_rate")
            )
            bin_df["lift"] = bin_df["good_rate"] / overall
            bin_df["count"] = df_clean.groupby(f"{feat}_bin").size().values
            reports[feat] = bin_df
        except Exception:
            continue
    return reports


def show_lift_analysis(df, target_col):
    import pandas as pd

    st.subheader("📊 Lift Analysis — Feature Predictive Power")
    if df is None or not target_col:
        st.warning("Load data and select a target first.")
        return

    # Imputation controls
    col1, col2 = st.columns(2)
    with col1:
        im_t = st.checkbox("Impute missing target", value=False)
        targ_m = st.selectbox("Target method", ["mean", "median", "most_frequent"], index=1, disabled=not im_t)
    with col2:
        im_f = st.checkbox("Impute missing features", value=True)
        feat_m = st.selectbox("Feature method", ["mean", "median", "most_frequent"], index=1, disabled=not im_f)

    # Build lift tables automatically when settings change
    settings = (target_col, im_t, targ_m, im_f, feat_m)
    if st.session_state.get("lift_meta") != settings:
        with st.spinner("Building lift tables…"):
            st.session_state.lift_reports = build_lift_reports(df, target_col, im_t, targ_m, im_f, feat_m)
            st.session_state.lift_meta = settings

    lift_reports = st.session_state.get("lift_reports", {})
    if not lift_reports:
        st.error("❌ No valid features for lift analysis.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_feat = st.selectbox("🎯 Select feature for lift analysis", list(lift_reports.keys()), key="lift_feature_selector")
    with col2:
        show_table = st.checkbox("📋 Show lift table", value=True)

    if not selected_feat:
        return

    lift_df = lift_reports[selected_feat]
    if show_table:
        def lift_cell_color(val):
            if val > 1:
                return 'background-color: green; color: white;'
            elif val < 1:
                return 'background-color: red; color: white;'
            else:
                return 'background-color: yellow; color: black;'

        styled_df = (
            lift_df.style
            .format({'good_rate': '{:.3f}', 'lift': '{:.3f}', 'count': '{:,.0f}'})
            .applymap(lift_cell_color, subset=['lift'])
        )
        st.write(f"**Lift Table for feature: {selected_feat}**")
        st.dataframe(styled_df)

    # Plot
    fig = go.Figure(go.Bar(
        x=lift_df[f'{selected_feat}_bin'].astype(str),
        y=lift_df['lift'],
        text=[f"{v:.2f}" for v in lift_df['lift']],
        textposition='outside',
        marker_color=['green' if v > 1 else 'red' if v < 1 else 'yellow' for v in lift_df["lift"]],
        customdata=np.stack([lift_df["good_rate"], lift_df["count"]], axis=-1),
        hovertemplate="Bin: %{x}<br>Lift: %{y:.3f}<br>Good rate: %{customdata[0]:.3f}<br>Count: %{customdata[1]:,}<extra></extra>"
    ))
    fig.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="Baseline (Lift = 1)")
    fig.update_layout(
        title=f"Predictive Power (Lift) — {selected_feat}",
        xaxis_title=f"{selected_feat} bins",
        yaxis_title="Lift",
        template="plotly_white",
        height=500,
        yaxis=dict(range=[0, max(1.2, lift_df['lift'].max() * 1.2)])
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Lift Summary")
        st.metric("Max Lift", f"{lift_df['lift'].max():.3f}")
        st.metric("Min Lift", f"{lift_df['lift'].min():.3f}")
        st.metric("Avg Lift", f"{lift_df['lift'].mean():.3f}")
    with c2:
        st.subheader("🎯 Predictive Power")
        strong_bins = sum(lift_df['lift'] > 1.2)
        weak_bins = sum(lift_df['lift'] < 0.8)
        st.metric("Strong Bins (>1.2)", strong_bins)
        st.metric("Weak Bins (<0.8)", weak_bins)
        lift_std = lift_df['lift'].std()
        strength = "High" if lift_std > 0.3 else "Medium" if 0.15 < lift_std <= 0.3 else "Low"
        st.metric("Feature Strength", strength)

    # Single interpretation block
    st.info(
        "📖 **Interpretation**\n"
        "- 🟢 **Lift > 1**: Bin has higher ‘good’ rate than average\n"
        "- 🔴 **Lift < 1**: Bin has lower ‘good’ rate than average\n"
        "- 🟡 **Lift ≈ 1**: Bin matches overall rate\n"
        "- **Feature Strength** uses lift variance: High (σ > 0.3), Medium (0.15–0.3), Low (≤ 0.15)"
    )
