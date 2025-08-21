import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.impute import SimpleImputer

# ---------- Utility Functions ----------
# ---------- Utility: target binning ----------
def bin_target_for_iv(s: pd.Series, method: str = "median", cutoff=None, q=0.5) -> pd.Series:
    """
    Returns a numeric 0/1 series where 1 = 'good', 0 = 'bad'.
    - method = 'median' (default): >= median -> 1 else 0
    - method = 'cutoff': >= cutoff -> 1 else 0
    - method = 'quantile': >= s.quantile(q) -> 1 else 0 (q in (0,1))
    """
    s = s.copy()
    if method == "median":
        thr = s.median()
        return (s >= thr).astype(int)
    elif method == "cutoff":
        if cutoff is None:
            raise ValueError("cutoff must be provided when method='cutoff'")
        return (s >= float(cutoff)).astype(int)
    elif method == "quantile":
        thr = s.quantile(float(q))
        return (s >= thr).astype(int)
    else:
        raise ValueError("Unknown binning method for target.")

def compute_iv(df, feature, target, bins=5):
    """
    Compute IV/WoE for a feature.
    Assumes 'target' is binary numeric (0/1). Does NOT mutate df.
    """
    try:
        tmp = df[[feature, target]].dropna().copy()
        if tmp.empty:
            return None, None

        # sanity: ensure binary 0/1
        uniq = set(tmp[target].unique())
        if not uniq.issubset({0, 1}):
            return None, None

        bin_col = f"{feature}_bin"
        tmp[bin_col] = pd.qcut(tmp[feature].rank(method="first"), q=bins, duplicates="drop")

        # Need at least 2 bins
        if tmp[bin_col].nunique() < 2:
            return None, None

        # Count Goods/Bads per bin
        bin_stats = tmp.groupby(bin_col)[target].agg(['count', 'sum'])
        bin_stats.rename(columns={"sum": "good"}, inplace=True)
        bin_stats["bad"] = bin_stats["count"] - bin_stats["good"]

        total_good = bin_stats["good"].sum()
        total_bad = bin_stats["bad"].sum()
        if total_good == 0 or total_bad == 0:
            # degenerate: all one class
            return None, None

        bin_stats["dist_good"] = bin_stats["good"] / (total_good + 1e-10)
        bin_stats["dist_bad"]  = bin_stats["bad"]  / (total_bad  + 1e-10)
        bin_stats["woe"] = np.log((bin_stats["dist_good"] + 1e-10) / (bin_stats["dist_bad"] + 1e-10))
        bin_stats["iv_bin"] = (bin_stats["dist_good"] - bin_stats["dist_bad"]) * bin_stats["woe"]
        iv_value = float(bin_stats["iv_bin"].sum())
        return bin_stats.reset_index(), iv_value
    except Exception:
        return None, None

def categorize_iv(iv_value):
    if iv_value < 0.02:
        return "Not useful"
    elif iv_value < 0.1:
        return "Weak"
    elif iv_value < 0.3:
        return "Medium"
    elif iv_value < 0.5:
        return "Strong"
    else:
        return "Suspicious / Too good"


# ---------- Main IV Analysis UI ----------

def show_iv_analysis(df, target_col=None, key_prefix: str = "iv"):
    """Add a unique key_prefix when calling from different pages/sections to avoid collisions.
       Requires `compute_iv` and `categorize_iv` to be defined in scope.
    """
    st.subheader("📊 Information Value (IV) — Feature Predictive Power")

    if df is None or df.empty:
        st.warning("⚠️ Load data first.")
        return

    # Helper for namespaced keys
    wkey = lambda name: f"{key_prefix}_{name}"

    # Helper: bin target into numeric 0/1
    def _bin_target_for_iv(s: pd.Series, method: str = "median", cutoff=None, q=0.5) -> pd.Series:
        """Returns a numeric 0/1 series where 1='good', 0='bad'."""
        if method == "median":
            thr = s.median()
            return (s >= thr).astype(int)
        elif method == "quantile":
            thr = s.quantile(float(q))
            return (s >= thr).astype(int)
        elif method == "cutoff":
            if cutoff is None:
                raise ValueError("cutoff must be provided when method='cutoff'")
            return (s >= float(cutoff)).astype(int)
        else:
            raise ValueError("Unknown binning method for target.")

    # ---- Column detection ----
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.warning("⚠️ No numeric columns detected.")
        return

    # ---- Target selector ----
    st.markdown("### 🎯 Select Target Variable")
    target_col = st.selectbox(
        "Choose Target",
        numeric_cols,
        index=0 if target_col is None else (
            numeric_cols.index(target_col) if target_col in numeric_cols else 0
        ),
        key=wkey("target_selector")
    )

    if not target_col or target_col not in df.columns:
        st.warning("Please select a valid target column.")
        return

    # ---- Target imputation + binning controls (like Lift) ----
    c1, c2, c3 = st.columns(3)
    with c1:
        impute_target = st.checkbox("Impute missing target", value=False, key=wkey("impute_target"))
        target_imp = st.selectbox(
            "Target method",
            ["mean", "median", "most_frequent"],
            index=1,
            disabled=not impute_target,
            key=wkey("target_imp_method"),
        )
    with c2:
        target_bin_method = st.selectbox(
            "Target binning for IV",
            ["median", "quantile", "cutoff"],
            index=0,
            key=wkey("target_bin_method"),
        )
    with c3:
        q_val = st.number_input(
            "Quantile (0–1)",
            min_value=0.0, max_value=1.0, value=0.5, step=0.05,
            disabled=(target_bin_method != "quantile"),
            key=wkey("q_val"),
        )
        cutoff_val = st.number_input(
            "Cutoff",
            value=0.0, step=0.1,
            disabled=(target_bin_method != "cutoff"),
            key=wkey("cutoff_val"),
        )

    # ---- Feature imputation + bin controls ----
    f1, f2 = st.columns(2)
    with f1:
        impute_feat = st.checkbox("Impute missing features", value=True, key=wkey("impute_feat"))
        feat_m = st.selectbox(
            "Feature method",
            ["mean", "median", "most_frequent"],
            index=1,
            disabled=not impute_feat,
            key=wkey("feat_method"),
        )
    with f2:
        feat_bins = st.selectbox(
            "Feature Bins (qcut)",
            [2,3,4,5,6,7,8,9,10],
            index=2,
            key=wkey("feat_bins"),
        )

    # ---- Clean copy & target handling ----
    df_clean = df.copy()

    # Target imputation (optional)
    if impute_target and df_clean[target_col].isna().any():
        df_clean[target_col] = SimpleImputer(strategy=target_imp).fit_transform(
            df_clean[[target_col]]
        ).ravel()

    # Drop rows with missing target after optional imputation
    df_clean = df_clean.dropna(subset=[target_col])

    # Bin target to numeric 0/1 for IV
    try:
        if target_bin_method == "median":
            df_clean["__iv_target__"] = _bin_target_for_iv(df_clean[target_col], method="median")
        elif target_bin_method == "quantile":
            df_clean["__iv_target__"] = _bin_target_for_iv(df_clean[target_col], method="quantile", q=q_val)
        else:
            df_clean["__iv_target__"] = _bin_target_for_iv(df_clean[target_col], method="cutoff", cutoff=cutoff_val)
    except Exception as e:
        st.error(f"Failed to bin target for IV: {e}")
        return

    # ---- Feature imputation (exclude target & __iv_target__) ----
    if impute_feat:
        num_cols_all = df_clean.select_dtypes(include="number").columns.tolist()
        feat_cols = [c for c in num_cols_all if c not in (target_col, "__iv_target__") and df_clean[c].isna().any()]
        if feat_cols:
            X = df_clean[feat_cols]

            # 1) Handle columns that are entirely NaN (mean/median can't compute)
            all_nan_cols = [c for c in feat_cols if X[c].isna().all()]
            if all_nan_cols:
                # choose a sensible default; 0 is common, or switch to 'most_frequent'
                df_clean[all_nan_cols] = 0.0
                # keep only the columns that still need imputation
                feat_cols = [c for c in feat_cols if c not in all_nan_cols]
                X = df_clean[feat_cols]

            # 2) If anything remains, impute and REWRAP as DataFrame to preserve shape/labels
            if feat_cols:
                imputer = SimpleImputer(strategy=feat_m)
                X_imp = imputer.fit_transform(X)             # ndarray (n_rows, n_cols)
                X_imp = pd.DataFrame(X_imp, columns=feat_cols, index=df_clean.index)
            df_clean[feat_cols] = X_imp

    # ---- Build IV reports using __iv_target__ ----
    iv_reports = {}
    feature_iv_scores = {}

    numeric_cols_iv = df_clean.select_dtypes(include="number").columns.tolist()
    candidate_feats = [c for c in numeric_cols_iv if c not in (target_col, "__iv_target__")]

    for feat in candidate_feats:
        # Skip low-variance / near-constant features (qcut cannot form bins)
        if df_clean[feat].nunique(dropna=True) < 5:
            continue
        bin_df, iv_val = compute_iv(df_clean, feat, "__iv_target__", bins=feat_bins)
        if bin_df is not None:
            iv_reports[feat] = bin_df
            feature_iv_scores[feat] = float(iv_val)

    if not iv_reports:
        st.error(
            "❌ No valid features for IV analysis.\n\n"
            "Tips:\n"
            "- Ensure the target can be binned (we support median/quantile/cutoff).\n"
            "- Choose features with enough unique values (≥5 recommended).\n"
            "- Avoid constant/ID-like columns."
        )
        return

    # ---- Feature selector ----
    s1, s2 = st.columns([3, 1])
    with s1:
        selected_feat = st.selectbox("🎯 Select feature", list(iv_reports.keys()), key=wkey("feature_selector"))
    with s2:
        show_table = st.checkbox("📋 Show IV table", value=True, key=wkey("show_table"))

    if not selected_feat:
        return

    iv_df = iv_reports[selected_feat]
    iv_val = feature_iv_scores[selected_feat]

    # ---- Table view ----
    if show_table:
        styled_df = (
            iv_df.style
            .format({'good': '{:.0f}', 'bad': '{:.0f}', 'dist_good': '{:.3f}', 'dist_bad': '{:.3f}', 'woe': '{:.3f}', 'iv_bin': '{:.3f}'})
        )
        st.write(f"**IV Table for feature: {selected_feat} (IV = {iv_val:.3f}, Strength = {categorize_iv(iv_val)})**")
        st.dataframe(styled_df, use_container_width=True)

    # ---- Plot WoE ----
    fig = go.Figure(go.Bar(
        x=iv_df[f"{selected_feat}_bin"].astype(str),
        y=iv_df["woe"],
        text=[f"{v:.2f}" for v in iv_df["woe"]],
        textposition='outside',
        marker_color="royalblue",
        hovertemplate="Bin: %{x}<br>WoE: %{y:.3f}<br>Good%: %{customdata[0]:.3f}<br>Bad%: %{customdata[1]:.3f}<extra></extra>",
        customdata=np.stack([iv_df["dist_good"], iv_df["dist_bad"]], axis=-1)
    ))
    fig.update_layout(
        title=f"Weight of Evidence (WoE) — {selected_feat}",
        xaxis_title=f"{selected_feat} bins",
        yaxis_title="WoE",
        template="plotly_white",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---- Summary metrics ----
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 IV Summary")
        st.metric("IV Value", f"{iv_val:.3f}")
        st.metric("Strength", categorize_iv(iv_val))
    with c2:
        st.subheader("🎯 Predictive Insight")
        st.metric("Max WoE", f"{iv_df['woe'].max():.3f}")
        st.metric("Min WoE", f"{iv_df['woe'].min():.3f}")
        st.metric("Avg WoE", f"{iv_df['woe'].mean():.3f}")

    # ---- All Features IV ranking ----
    st.markdown("### 📊 IV Ranking Across Features")
    iv_rank_df = pd.DataFrame(
        sorted(feature_iv_scores.items(), key=lambda x: x[1], reverse=True),
        columns=["Feature", "IV"]
    )
    iv_rank_df["Strength"] = iv_rank_df["IV"].apply(categorize_iv)
    st.dataframe(iv_rank_df.style.format({'IV': '{:.3f}'}), use_container_width=True)

    # ---- Interpretation ----
    st.info(
        "📖 **Information Value (IV) Procedure**\n"
        "1. Bin feature values\n"
        "2. Compute Good% and Bad% in each bin\n"
        "3. Calculate Weight of Evidence (WoE = ln(%Good/%Bad))\n"
        "4. Compute IV per bin = (%Good - %Bad) × WoE\n"
        "5. Sum across bins → IV(feature)\n\n"
        "**Guidelines:**\n"
        "- <0.02 → Not useful\n"
        "- 0.02–0.1 → Weak\n"
        "- 0.1–0.3 → Medium\n"
        "- 0.3–0.5 → Strong\n"
        "- >0.5 → Suspicious (possible data leakage)"
    )
