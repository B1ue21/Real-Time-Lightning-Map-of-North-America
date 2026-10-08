import io
import re
from datetime import datetime, timedelta, timezone

import boto3
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import xarray as xr
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "noaa-goes19"
PRODUCT = "GLM-L2-LCFA"
UTC = timezone.utc
WEST, EAST, SOUTH, NORTH = -125, -66, 24, 50

st.set_page_config(page_title="Live lightning map", layout="wide")
st.title("Live lightning flash map")
st.caption("NOAA GOES-19 GLM | Refreshes every 60 seconds | Times are UTC")
minutes = st.sidebar.slider("Minutes of lightning to display", 5, 30, 10)


@st.cache_resource
def s3_client():
    return boto3.client(
        "s3", region_name="us-east-1",
        config=Config(
            signature_version=UNSIGNED, connect_timeout=10, read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def filename_time(key, marker):
    match = re.search(rf"_{marker}(\d{{13}})", key)
    if not match:
        raise ValueError(f"Missing timestamp in {key}")
    return datetime.strptime(match.group(1), "%Y%j%H%M%S").replace(tzinfo=UTC)


@st.cache_data(ttl=30, show_spinner=False)
def list_hour(prefix):
    keys = []
    paginator = s3_client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        keys.extend(
            item["Key"] for item in page.get("Contents", [])
            if item["Key"].endswith(".nc")
        )
    return keys


def recent_files(start, end):
    hour = (start - timedelta(minutes=1)).replace(minute=0, second=0, microsecond=0)
    keys = []
    while hour <= end:
        keys.extend(list_hour(f"{PRODUCT}/{hour:%Y}/{hour:%j}/{hour:%H}/"))
        hour += timedelta(hours=1)
    return sorted(
        key for key in set(keys)
        if filename_time(key, "e") >= start and filename_time(key, "s") <= end
    )


@st.cache_data(ttl=3600, max_entries=500, show_spinner=False)
def read_flashes(key):
    response = s3_client().get_object(Bucket=BUCKET, Key=key)
    body = response["Body"]
    try:
        content = body.read()
    finally:
        body.close()
    with xr.open_dataset(io.BytesIO(content), engine="h5netcdf", decode_times=True) as ds:
        lat = ds["flash_lat"].values
        lon = ds["flash_lon"].values
        times = ds["flash_time_offset_of_first_event"].values
        valid = (
            np.isfinite(lat) & np.isfinite(lon)
            & (lat >= SOUTH) & (lat <= NORTH)
            & (lon >= WEST) & (lon <= EAST)
        )
        if "flash_quality_flag" in ds:
            valid &= ds["flash_quality_flag"].values == 0
        return pd.DataFrame({
            "latitude": lat[valid], "longitude": lon[valid],
            "time": pd.to_datetime(times[valid], utc=True),
        })


@st.fragment(run_every="60s")
def live_plot():
    now = datetime.now(UTC)
    start = now - timedelta(minutes=minutes)
    try:
        with st.spinner("Checking NOAA for recent data..."):
            keys = recent_files(start, now)
    except Exception as exc:
        st.error(f"Could not list NOAA data: {exc}")
        return
    if not keys:
        st.warning("No NOAA files available in the selected time window. Retrying next refresh.")
        return
    frames, successful, errors = [], [], []
    progress = st.progress(0, text="Loading lightning observations...")
    for index, key in enumerate(keys):
        try:
            frames.append(read_flashes(key))
            successful.append(key)
        except Exception as exc:
            errors.append(f"{key.rsplit('/', 1)[-1]}: {exc}")
        progress.progress((index + 1) / len(keys), text=f"Loaded {index + 1} of {len(keys)} files")
    progress.empty()
    if errors:
        st.warning(f"{len(errors)} file(s) could not be loaded; observations may be incomplete.")
        with st.expander("Show loading errors"):
            st.code("\n".join(errors))
    if not successful:
        st.error("Could not read any NOAA files. Retrying next refresh.")
        return
    latest = max(filename_time(key, "e") for key in successful)
    lag = max(0, (now - latest).total_seconds() / 60)
    st.caption(
        f"Checked: {now:%Y-%m-%d %H:%M:%S} UTC | "
        f"Latest loaded observation: {latest:%H:%M:%S} UTC | Data lag: {lag:.1f} minutes"
    )
    if lag > 5:
        st.warning("The latest loaded observations are over 5 minutes old.")
    data = pd.concat(frames, ignore_index=True)
    data = data.loc[data["time"].between(start, now)].copy()
    data["age_minutes"] = (pd.Timestamp(now) - data["time"]).dt.total_seconds() / 60
    data["time_utc"] = data["time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.metric("Detected flashes in viewing area", f"{len(data):,}")
    if data.empty:
        st.info("No qualifying flashes found in this area and time window. Continuing to refresh.")
    fig = px.scatter_geo(
        data, lat="latitude", lon="longitude", color="age_minutes",
        range_color=(0, minutes),
        color_continuous_scale=[[0, "#fff700"], [0.5, "#ff7b00"], [1, "#6b27b5"]],
        hover_data={"latitude": ":.3f", "longitude": ":.3f", "time_utc": True, "age_minutes": ":.1f"},
        labels={
            "longitude": "Longitude (degrees)",
            "latitude": "Latitude (degrees)",
            "age_minutes": "Age (minutes)",
        },
    )
    fig.update_traces(marker={"size": 5, "opacity": 0.8})
    fig.update_geos(
        projection_type="mercator", lonaxis_range=[WEST, EAST], lataxis_range=[SOUTH, NORTH],
        showland=True, landcolor="#172537", showocean=True, oceancolor="#0b1420",
        showcountries=True, countrycolor="#607080", showsubunits=True, subunitcolor="#405060",
        showcoastlines=True, coastlinecolor="#607080", bgcolor="#0b1420",
    )
    fig.update_layout(
        height=650, margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="#0b1420", font_color="white", uirevision="keep-map-view",
    )
    st.plotly_chart(fig, use_container_width=True)


live_plot()
st.caption("Source: NOAA GOES-19 GLM L2 LCFA, accessed through public AWS data. Points represent flashes, including in-cloud lightning.")
