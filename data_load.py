import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional
import snowflake.connector
import os
import json
import multiprocessing
import re
import traceback
import warnings
from dataclasses import dataclass
from multiprocessing.pool import ThreadPool
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Optional, Union
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
 

default_path = "/home/oneai/analysis/eda_app/data/lantus_stage_08_data.csv"  

def show_data_load(default_target: str = "ge_dup_p2_c3p1_3k_bioreactor_vcd_day3") -> tuple[Optional[pd.DataFrame], Optional[str], list[str], list[str]]:
    """
    Display the Data Load tab (defaulting to Manual Upload with default file path loaded).
    """
    st.subheader("📥 Load Data")

    # Default to Manual Upload instead of Snowflake
    load_source = st.radio("Select Data Source:", ["Snowflake", "Manual Upload"], index=1, horizontal=True)

    df = None

    if load_source == "Snowflake":
        # ---------------- Snowflake Option ----------------
        schema_name = st.text_input("Enter Schema Name", value="CMP_SIMPLY")
        table_name = st.text_input("Enter Table Name", value="MASTER_ML")
        plant_id = st.text_input("Enter Plant ID", value="")
        stage_name = st.text_input("Enter Stage", value="")

        if st.button("Load & Pivot Data"):
            with st.spinner("Fetching data from Snowflake..."):
                try:
                    df_raw = read_source_table(schema_name, table_name)
                    if plant_id:
                        df_raw = df_raw[df_raw["plant_id"].str.lower() == plant_id.strip().lower()]
                    if stage_name:
                        df_raw = df_raw[df_raw["stage"].str.lower() == stage_name.strip().lower()]
                    df = pivot_master_data(df_raw)
                    st.session_state["df"] = df
                    st.success(f"✅ Loaded {df.shape[0]:,} rows and {df.shape[1]:,} columns from Snowflake.")
                except Exception as e:
                    st.error(f"❌ Error loading data: {e}")
                    st.code(traceback.format_exc(), language="python")

    else:
        # ---------------- Manual Upload Option (Default) ----------------
        manual_method = st.radio("Select Method:", ["Upload CSV", "Enter File Path"], index=1)

        if manual_method == "Upload CSV":
            uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.session_state["df"] = df
                    st.success("✅ File uploaded successfully.")
                except Exception as e:
                    st.error(f"❌ Error reading file: {e}")
                    st.code(traceback.format_exc(), language="python")

        else:
            # Auto-load default path if exists
            file_path = st.text_input("Enter full file path:", value=default_path)
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    st.session_state["df"] = df
                    st.success(f"✅ Loaded file from: {file_path}")
                except Exception as e:
                    st.error(f"❌ Error reading file: {e}")
                    st.code(traceback.format_exc(), language="python")
            else:
                st.warning("⚠️ File not found.")

    # ---------------- Preview ----------------
    if "df" in st.session_state:
        st.write("### Preview of Data")
        st.dataframe(st.session_state["df"].head(50), use_container_width=True)
    else:
        st.info("ℹ️ Load data to use it in other tabs.")

    # ---------------- Prepare Outputs ----------------
    df = st.session_state.get("df")
    numeric_cols = df.select_dtypes(include="number").columns.tolist() if df is not None else []
    target_col = (
        st.sidebar.selectbox(
            "🎯 Select target column",
            options=numeric_cols if numeric_cols else ["(no numeric columns)"],
            index=(numeric_cols.index(default_target) if (df is not None and default_target in numeric_cols) else 0),
            disabled=not bool(numeric_cols),
        )
        if df is not None
        else None
    )

    valid_default_corr_features = (
        [c for c in [] if df is not None and c in numeric_cols and (target_col and c != target_col)]
        if (numeric_cols and target_col)
        else []
    )

    return df, target_col, numeric_cols, valid_default_corr_features




@dataclass
class SnowflakeAuthentication:
    """
    Dataclass for combining all relevant information for snowflake authentication
    """
    account: str
    warehouse: str
    database: str
    role: str



def _get_snowflake_connection(
    schema: Optional[str] = None, custom_conf: Optional[dict] = None
) -> snowflake.connector.SnowflakeConnection:
    """
    This is a helper function to connect to SimplY Snowflake database
    based on the credentials specified in the config file and oneAI's secrets
    and return the connection.
    @param schema: Optional[str] with default to None. Name of the schema to connect to
    @param custom_conf: Dict with SnowflakeAuthentication attributes to overwrite
    @return: SnowflakeConnection
    """
    # Load snowflake configuration yml file
    config  = {"snowflake_authentication":{"dev":{
    "account": "sanofi-emea_ia",
    "warehouse": "SIMPLY_DEV_WH_TRANSFORM",
    "database": "SIMPLY_DEV",
    "role": "SIMPLY_DEV_TRANSFORM_PROC"
}}}

    # get local user and password from oneAI secrets corresponding to the current environment
    user = os.getenv("SNOWFLAKE_USER")

    if not user:
        raise ValueError("Var SNOWFLAKE_USER' must be set")

    # get environment value from one AI secrets corresponding to the current environment
    environment = os.getenv("ENVIRONMENT")

    # Determine the db connection based on the environment
    if environment == "PRODUCTION":
        # Run on SIMPLY_PROD
        passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").encode()
        file_path = Path(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", ""))
        with file_path.open("rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(), password=passphrase, backend=default_backend()
            )
        config_for_env = config["snowflake_authentication"]["prod"]
    elif environment == "STAGING":
        # Run on SIMPLY_UAT
        passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").encode()
        file_path = Path(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", ""))
        with file_path.open("rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(), password=passphrase, backend=default_backend()
            )
        config_for_env = config["snowflake_authentication"]["uat"]
    else:
        # Run on SIMPLY_DEV (default fallback option)
        passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").encode()
        file_path = Path("/home/oneai/oneai-dda-simply-prj0060876_ml/keys/dev_transform_pk.p8")
        with file_path.open("rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(), password=passphrase, backend=default_backend()
            )
        config_for_env = config["snowflake_authentication"]["dev"]

    snowflake_config = SnowflakeAuthentication(**config_for_env)
    if custom_conf:
        for key, val in custom_conf.items():
            setattr(snowflake_config, key, val)

    # establish connectionn
    connection = snowflake.connector.connect(
        user=user,
        private_key=p_key,
        account=snowflake_config.account,
        warehouse=snowflake_config.warehouse,
        database=snowflake_config.database,
        role=snowflake_config.role,
        schema=schema,
    )

    return connection


def _query_snowflake_table(sql_query: str) -> pd.DataFrame:
    """
    Wrap snowflake table queries into its own function
    @param sql_query: SQL query string that is going to be executed in snowflake
    @return: pandas Data Frame with the query results
    """
    connection = _get_snowflake_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(sql_query)
    except Exception:
        connection.rollback()
        raise
    else:
        data_frame: pd.DataFrame = cursor.fetch_pandas_all()
        data_frame.columns = data_frame.columns.str.lower()
        return data_frame
    finally:
        cursor.close()
        connection.close()


def read_source_table(schema_name: str, table_name: str) -> pd.DataFrame:
    """
    This function reads an entire table from SimplY snowflake
    defined by schema_name and table_name.

    This is a generic and implicit function that executes a SELECT * statement.

    @param schema_name: str. Name of the schema in snowflake to read from
    @param table_name: str. Name of the table in snowflake to read from
    @return: pd.DataFrame
    """
    query_load_source_tables = f"""
        select * from {schema_name}."{table_name}"
    """
    data_frame = _query_snowflake_table(query_load_source_tables)
    return data_frame


def pivot_master_data(master_data: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots the data from the master table to have one feature per column.
    @param master_data: DataFrame from MASTER_ML
    @return: melted MASTER_ML DataFrame
    """

    pivoted_data = master_data.pivot_table(
        index=['batch_id', 'material_id', 'plant_id', 'stage', 'manufacture_date', 'product_name'],
        columns="feature_name",
        values="feature_value",
        aggfunc=lambda x: pd.to_numeric(x, errors="coerce").astype(float),
        fill_value=np.nan,
    ).reset_index()
    return pivoted_data
