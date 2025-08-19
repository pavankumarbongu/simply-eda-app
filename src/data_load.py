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
import glob

from src.config import PLANT_SITE_MAP, SCHEMA_NAME, TABLE_NAME

default_path = "/home/oneai/simply-eda-app/data/frankfurt/08/frankfurt_08_data.csv"  

import os
import traceback
from pathlib import Path
import pandas as pd
import streamlit as st

def show_data_load(default_path: str = "/home/oneai/simply-eda-app/data/frankfurt/08/frankfurt_08_data.csv") -> pd.DataFrame:
    """
    Display the Data Load tab (defaulting to Manual Upload with default file path loaded).
    Handles both Snowflake and Manual Upload but only returns the dataframe.
    """

    st.subheader("📥 Load Data")

    # Default to Manual Upload instead of Snowflake
    load_source = st.radio("Select Data Source:", ["Snowflake", "Manual Upload"], index=1, horizontal=True)

    df = None

    if load_source == "Snowflake":
        # ---------------- Snowflake Option ----------------
        schema_name = SCHEMA_NAME
        table_name = TABLE_NAME

        # Dict: {plant_id: [stage1, stage2, ...]}
        plant_stage_map = get_plant_stage_mapping(schema_name, table_name)

        # Select site (maps to plant_id)
        selected_site = st.selectbox("Select Site", list(PLANT_SITE_MAP.keys()))
        plant_id = PLANT_SITE_MAP[selected_site]

        # Stage dropdown (only if stages exist for this plant_id)
        stages = plant_stage_map.get(plant_id, [])
        stage_name = st.selectbox("Select Stage", stages) if stages else None

        # Define save path
        if plant_id and stage_name:
            folder_path = Path(f"data/{selected_site}/{stage_name}")
            folder_path.mkdir(parents=True, exist_ok=True)  # auto-create if not exists
            file_path = folder_path / f"{selected_site}_{stage_name}_data.csv"
        else:
            file_path = None

        col1, col2 = st.columns(2)

        if col1.button("📂 Load Existing from File"):
            if not (plant_id and stage_name):
                st.error("❌ Please enter both Plant ID and Stage to continue.")
            elif file_path and file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    st.session_state["df"] = df
                    st.success(f"✅ Loaded data from {file_path}")
                except Exception as e:
                    st.error(f"❌ Error reading existing file: {e}")
                    st.code(traceback.format_exc(), language="python")
            else:
                st.warning("⚠️ File not found locally. Fetching from Snowflake instead...")
                try:
                    df_raw = read_source_table(schema_name, table_name, plant_id, stage_name)
                    df = pivot_master_data(df_raw)
                    df.to_csv(file_path, index=False)
                    st.session_state["df"] = df
                    st.success(f"✅ Loaded from Snowflake & saved to {file_path}")
                except Exception as e:
                    st.error(f"❌ Error fetching from Snowflake: {e}")
                    st.code(traceback.format_exc(), language="python")

        if col2.button("🔄 Load New from Snowflake"):
            if not (plant_id and stage_name):
                st.error("❌ Please enter both Plant ID and Stage to continue.")
            else:
                with st.spinner("Fetching NEW data from Snowflake..."):
                    try:
                        df_raw = read_source_table(schema_name, table_name, plant_id, stage_name)
                        df = pivot_master_data(df_raw)
                        df.to_csv(file_path, index=False)
                        st.session_state["df"] = df
                        st.success(f"✅ Loaded {df.shape[0]:,} rows & {df.shape[1]:,} cols from Snowflake and saved to {file_path}")
                    except Exception as e:
                        st.error(f"❌ Error loading from Snowflake: {e}")
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

    # Return only the dataframe
    return st.session_state.get("df")



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


def read_source_table(schema_name: str, table_name: str, plant_id: Optional[str] = None, stage_name: Optional[str] = None) -> pd.DataFrame:
    """
    Reads data from Snowflake with optional filters for plant_id and stage.

    @param schema_name: str. Name of the schema in Snowflake
    @param table_name: str. Name of the table in Snowflake
    @param plant_id: Optional[str]. Plant ID to filter
    @param stage_name: Optional[str]. Stage to filter
    @return: pd.DataFrame
    """

    # Base query
    query = f'SELECT * FROM {schema_name}."{table_name}" WHERE 1=1'

    # Add filters if provided
    if plant_id:
        query += f" AND LOWER(plant_id) = '{plant_id.strip().lower()}'"
    if stage_name:
        query += f" AND LOWER(stage) = '{stage_name.strip().lower()}'"

    # Run query
    data_frame = _query_snowflake_table(query)
    return data_frame

from collections import defaultdict

def get_plant_stage_mapping(schema_name: str, table_name: str) -> dict[str, list[str]]:
    """
    Fetch unique plant_id → stage mappings from Snowflake.

    @param schema_name: str
    @param table_name: str
    @return: dict where key=plant_id, value=list of stages
    """
    query = f"""
        SELECT DISTINCT LOWER(plant_id) AS plant_id, LOWER(stage) AS stage
        FROM {schema_name}."{table_name}"
        WHERE plant_id IS NOT NULL AND stage IS NOT NULL
    """
    df = _query_snowflake_table(query)

    mapping = defaultdict(list)
    for _, row in df.iterrows():
        mapping[row["plant_id"]].append(row["stage"])

    # sort stages for consistency
    return {k: sorted(set(v)) for k, v in mapping.items()}


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
