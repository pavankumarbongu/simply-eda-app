import pandas as pd
import numpy as np
import streamlit as st

def univariate_feature_summary(df: pd.DataFrame, lower_pct=5, upper_pct=95) -> pd.DataFrame:
    summary = []
    for col in df.columns:
        series = df[col]
        dtype = series.dtype
        n_unique = series.nunique(dropna=True)
        n_missing = series.isnull().sum()
        perc_missing = (n_missing / len(series)) * 100

        if np.issubdtype(dtype, np.number):
            var = series.var()
            mean = series.mean()
            median = series.median()
            std = series.std()
            min_val = series.min()
            max_val = series.max()

            # Percentile-based outlier detection
            non_na = series.dropna()
            if not non_na.empty:
                lower_bound = np.percentile(non_na, lower_pct)
                upper_bound = np.percentile(non_na, upper_pct)
                outliers = non_na[(non_na < lower_bound) | (non_na > upper_bound)]
                n_outliers = outliers.count()
                perc_outliers = (n_outliers / len(series)) * 100
            else:
                lower_bound = upper_bound = np.nan
                n_outliers = perc_outliers = np.nan
        else:
            var = mean = median = std = min_val = max_val = np.nan
            lower_bound = upper_bound = np.nan
            n_outliers = perc_outliers = np.nan

        mode_val = series.mode(dropna=True)
        if not mode_val.empty:
            top_value = str(mode_val.iloc[0])  # 🔑 ensure string for Arrow compatibility
            top_freq = (series == mode_val.iloc[0]).sum()
        else:
            top_value = np.nan
            top_freq = np.nan

        summary.append({
            "feature": col,
            "dtype": str(dtype),
            "n_unique": n_unique,
            "variance": var,
            "n_missing": n_missing,
            "%missing": perc_missing,
            "mean": mean,
            "median": median,
            "std_dev": std,
            "min": min_val,
            "max": max_val,
            "top_value": top_value,
            "top_freq": top_freq,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "n_outliers": n_outliers,
            "%outliers": perc_outliers
        })
    return pd.DataFrame(summary)


def show_data_summary(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("📋 Data Summary (Univariate)")
    if df is None or df.empty:
        st.warning("No data loaded.")
        return pd.DataFrame()

    # Outlier percentile inputs
    st.markdown("**Outlier detection thresholds**")
    col1, col2 = st.columns(2)
    with col1:
        lower_pct = st.slider("Lower percentile", 0, 20, 5)
    with col2:
        upper_pct = st.slider("Upper percentile", 80, 100, 95)

    # Build summary
    df_summary = univariate_feature_summary(df, lower_pct, upper_pct)

    # KPIs
    numeric_rows = df_summary[df_summary["variance"].notna()]
    n_numeric = numeric_rows.shape[0]
    n_non_numeric = (df_summary["variance"].isna()).sum()
    high_missing_cols = df_summary[df_summary["%missing"] >= 50].shape[0]
    n_unique_eq_1 = (df_summary["n_unique"] == 1).sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Numeric features", f"{n_numeric:,}")
    k2.metric("Non-numeric features", f"{n_non_numeric:,}")
    k3.metric("Cols ≥50% missing", f"{high_missing_cols:,}")
    k4.metric("Cols with n_unique = 1", f"{n_unique_eq_1:,}")

    # Highlighting
    def highlight_missing(val):
        try:
            v = float(val)
        except Exception:
            return ""
        return "background-color: #ffd6d6; color: black;" if v >= 50 else ""

    def highlight_outliers(val):
        try:
            v = float(val)
        except Exception:
            return ""
        return "background-color: #fff2cc; color: black;" if v >= 10 else ""

    styled = (
        df_summary.style
        .format({
            "variance": "{:.4f}",
            "mean": "{:.4f}",
            "median": "{:.4f}",
            "std_dev": "{:.4f}",
            "min": "{:.4f}",
            "max": "{:.4f}",
            "%missing": "{:.2f}",
            "%outliers": "{:.2f}",
        }, na_rep="-")
        .applymap(highlight_missing, subset=["%missing"])
        .applymap(highlight_outliers, subset=["%outliers"])
    )
    st.dataframe(styled, use_container_width=True, height=420)

    # Filters
    st.markdown("---")
    st.markdown("### 🎛️ Filters")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        min_unique = st.number_input("Min n_unique", min_value=1, value=2, step=1)
    with c2:
        dtype_filter = st.selectbox("Dtype filter", ["Numeric only", "All types"], index=0)
    with c3:
        max_missing = st.slider("Max %missing", 0, 100, 80, 1)
    with c4:
        min_variance = st.number_input("Min variance (numeric)", value=0.0, step=0.001)

    filtered = df_summary.copy()
    filtered = filtered[filtered["n_unique"] > (min_unique - 1)]
    if dtype_filter == "Numeric only":
        filtered = filtered[filtered["dtype"].str.contains("float|int|number|decimal", case=False, na=False)]
    filtered = filtered[filtered["%missing"] <= max_missing]
    filtered = filtered[(filtered["variance"].isna()) | (filtered["variance"] >= min_variance)].reset_index(drop=True)

    st.markdown("#### 🔽 Filtered Results")
    if filtered.empty:
        st.warning("No rows match the current filters.")
    else:
        st.dataframe(
            filtered.style.format({
                "variance": "{:.4f}",
                "mean": "{:.4f}",
                "median": "{:.4f}",
                "std_dev": "{:.4f}",
                "min": "{:.4f}",
                "max": "{:.4f}",
                "%missing": "{:.2f}",
                "%outliers": "{:.2f}",
            }, na_rep="-"),
            use_container_width=True,
            height=360
        )
    return filtered
