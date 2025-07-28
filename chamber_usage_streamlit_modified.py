import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
from chamber_usage import login, get_allocation, count_weekends_and_holidays

# Helper to extract monthly usage by status
def extract_monthly_status_percentages(chamber_data):
    monthly_status = {}
    for entry in chamber_data:
        if isinstance(entry, list):
            for category_dict in entry:
                for category in category_dict.values():
                    month = category['actual_month']
                    status = category['type']
                    monthly_status.setdefault(month, {}).setdefault(status, 0)
                    monthly_status[month][status] += category['percentage']
        elif isinstance(entry, dict):
            month = entry['actual_month']
            status = entry['type']
            monthly_status.setdefault(month, {}).setdefault(status, 0)
            monthly_status[month][status] += entry['percentage']
    return monthly_status

# Plot stacked bar chart for one chamber
def plot_stacked_chart(chamber_data, title):
    monthly_status = extract_monthly_status_percentages(chamber_data)
    months = sorted(monthly_status.keys())
    all_statuses = sorted({status for month in monthly_status.values() for status in month})

    fig = go.Figure()
    for status in all_statuses:
        values = [monthly_status[month].get(status, 0) for month in months]
        fig.add_trace(go.Bar(name=status, x=months, y=values))

    fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="60% Limit", annotation_position="top left")
    fig.update_layout(barmode='stack', title=title, yaxis_title="Usage %")
    return fig

# Plot combined usage of BIG and SMALL chambers
def plot_combined_usage(big_data, small_data):
    big_monthly = extract_monthly_status_percentages(big_data)
    small_monthly = extract_monthly_status_percentages(small_data)
    all_months = sorted(set(big_monthly.keys()).union(small_monthly.keys()))
    combined = {}
    for month in all_months:
        combined[month] = {}
        for status in set(big_monthly.get(month, {}).keys()).union(small_monthly.get(month, {}).keys()):
            combined[month][status] = (big_monthly.get(month, {}).get(status, 0) + small_monthly.get(month, {}).get(status, 0))/2

    fig = go.Figure()
    all_statuses = sorted({status for month in combined.values() for status in month})
    for status in all_statuses:
        values = [combined[month].get(status, 0) for month in all_months]
        fig.add_trace(go.Bar(name=status, x=all_months, y=values))

    fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="60% Limit", annotation_position="top left")
    fig.update_layout(barmode='stack', title="Összesített kihasználtság (BIG + SMALL)", yaxis_title="Usage %")
    return fig

st.set_page_config(layout="wide")

# Streamlit UI
st.title("Zajkamra kihasználtság elemzés")

with st.sidebar:
    st.header("Bejelentkezés")
    user = st.text_input("Felhasználónév")
    password = st.text_input("Jelszó", type="password")

    st.header("Időszak kiválasztása")
    col1, col2 = st.columns(2)
    with col1:
        start_year = st.number_input("Kezdő év", min_value=2020, max_value=2100, value=2024)
        start_month = st.number_input("Kezdő hónap", min_value=1, max_value=12, value=1)
    with col2:
        end_year = st.number_input("Befejező év", min_value=2020, max_value=2100, value=datetime.today().year)
        end_month = st.number_input("Befejező hónap", min_value=1, max_value=12, value=datetime.today().month)

    compare = st.checkbox("Összehasonlítás második időszakkal")
    if compare:
        st.markdown("**Második időszak**")
        col3, col4 = st.columns(2)
        with col3:
            start_year2 = st.number_input("Kezdő év 2", min_value=2020, max_value=2100, value=2023)
            start_month2 = st.number_input("Kezdő hónap 2", min_value=1, max_value=12, value=1)
        with col4:
            end_year2 = st.number_input("Befejező év 2", min_value=2020, max_value=2100, value=2023)
            end_month2 = st.number_input("Befejező hónap 2", min_value=1, max_value=12, value=12)

if st.button("Elemzés indítása"):
    if not user or not password:
        st.error("Kérlek add meg a bejelentkezési adatokat.")
    else:
        session = requests.Session()
        session.auth = (user.strip(), password.strip())
        login(session)

        def collect_data(start_year, start_month, end_year, end_month):
            current = datetime(start_year, start_month, 1)
            end = datetime(end_year, end_month, 1)
            if end.month == 12:
                end = end.replace(year=end.year + 1, month=1)
            else:
                end = end.replace(month=end.month + 1)

            all_resource_usages_ = {
                "BIG noise chamber": [],
                "SMALL noise chamber": []
            }

            while current < end:
                first_day = current.replace(day=1)
                if current.month == 12:
                    next_month = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    next_month = current.replace(month=current.month + 1, day=1)
                last_day = next_month - timedelta(days=1)

                start = first_day.strftime("%Y-%m-%d")
                end_ = last_day.strftime("%Y-%m-%d")
                weekends, holidays, _, all_days = count_weekends_and_holidays(start, end_)
                _, _, _, _, resource_usage_ = get_allocation(session, weekends, holidays, all_days, start, end_)

                for chamber in ["BIG noise chamber", "SMALL noise chamber"]:
                    all_resource_usages_[chamber].append(resource_usage_.get(chamber, {}))

                current = next_month

            return all_resource_usages_

        data1 = collect_data(start_year, start_month, end_year, end_month)
        st.subheader("BIG zajkamra")
        st.plotly_chart(plot_stacked_chart(data1["BIG noise chamber"], "BIG zajkamra kihasználtság"))

        st.subheader("SMALL zajkamra")
        st.plotly_chart(plot_stacked_chart(data1["SMALL noise chamber"], "SMALL zajkamra kihasználtság"))

        st.subheader("Összesített kihasználtság")
        st.plotly_chart(plot_combined_usage(data1["BIG noise chamber"], data1["SMALL noise chamber"]))

        if compare:
            data2 = collect_data(start_year2, start_month2, end_year2, end_month2)
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("BIG zajkamra - első időszak")
                st.plotly_chart(plot_stacked_chart(data1["BIG noise chamber"], "BIG zajkamra - első időszak"), use_container_width=True)
            with col2:
                st.subheader("BIG zajkamra - második időszak")
                st.plotly_chart(plot_stacked_chart(data2["BIG noise chamber"], "BIG zajkamra - második időszak"), use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                st.subheader("SMALL zajkamra - első időszak")
                st.plotly_chart(plot_stacked_chart(data1["SMALL noise chamber"], "SMALL zajkamra - első időszak"))
            with col4:
                st.subheader("SMALL zajkamra - második időszak")
                st.plotly_chart(plot_stacked_chart(data2["SMALL noise chamber"], "SMALL zajkamra - második időszak"))

