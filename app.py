"""Streamlit application entry point."""

import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(page_title="FactoryOps", layout="wide")

# Configure these values in Streamlit Cloud -> App -> Settings -> Secrets.
# Use only the publishable Supabase key; never use a database password or
# service-role key in Streamlit Cloud.
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if "access_token" in st.session_state:
    try:
        supabase.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"],
        )
    except Exception:
        st.session_state.clear()
        st.rerun()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("FactoryOps Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state.user = response.user
            st.session_state.access_token = response.session.access_token
            st.session_state.refresh_token = response.session.refresh_token
            st.success("Login successful.")
            st.rerun()
        except Exception as error:
            st.error(f"Login failed: {error}")

    st.stop()

if st.sidebar.button("Log out"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.rerun()


page = st.sidebar.radio(
    "Factory Modules",
    [
        "Dashboard",
        "Orders",
        "Production",
        "Inventory",
        "Maintenance",
        "Quality",
        "Workforce",
        "Purchasing",
        "Costs",
        "Safety",
    ],
)


def load_table(table_name: str) -> pd.DataFrame:
    """Load a Supabase table into a DataFrame for the selected module."""
    response = supabase.table(table_name).select("*").execute()
    return pd.DataFrame(response.data)


try:
    if page == "Dashboard":
        production_df = load_table("production_records")
        orders_df = load_table("customer_orders")
        inventory_df = load_table("inventory")
        machines_df = load_table("machines")
        alerts_df = load_table("factory_alerts")

        st.title("Factory Manager Dashboard")

        total_production = (
            production_df["actual_quantity"].sum()
            if not production_df.empty else 0
        )
        planned_production = (
            production_df["planned_quantity"].sum()
            if not production_df.empty else 0
        )
        rejected_units = (
            production_df["rejected_quantity"].sum()
            if not production_df.empty else 0
        )
        downtime_minutes = (
            production_df["downtime_minutes"].sum()
            if not production_df.empty else 0
        )
        active_orders = (
            len(orders_df[orders_df["status"].isin(["pending", "in production"])])
            if not orders_df.empty else 0
        )
        open_machines = (
            len(machines_df[machines_df["status"] != "operational"])
            if not machines_df.empty else 0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Actual Production", f"{total_production:,.0f}")
        col2.metric("Planned Production", f"{planned_production:,.0f}")
        col3.metric("Active Orders", active_orders)
        col4.metric("Rejected Units", f"{rejected_units:,.0f}")

        col5, col6 = st.columns(2)
        col5.metric("Downtime", f"{downtime_minutes:,.0f} minutes")
        col6.metric("Machines Requiring Attention", open_machines)

        st.subheader("Production Performance")

        if not production_df.empty:
            production_df["efficiency"] = (
                production_df["actual_quantity"]
                / production_df["planned_quantity"]
                * 100
            ).round(1)

            st.dataframe(
                production_df[
                    [
                        "production_date",
                        "planned_quantity",
                        "actual_quantity",
                        "rejected_quantity",
                        "downtime_minutes",
                        "efficiency",
                    ]
                ],
                use_container_width=True,
            )
        else:
            st.info("No production records available.")

        st.subheader("Machines Requiring Attention")

        if not machines_df.empty:
            attention_machines = machines_df[
                machines_df["status"] != "operational"
            ]

            if not attention_machines.empty:
                st.warning("Some machines require attention.")
                st.dataframe(attention_machines, use_container_width=True)
            else:
                st.success("All machines are operational.")

    elif page == "Orders":
        st.title("Orders and Demand")
        orders_df = load_table("customer_orders")

        if orders_df.empty:
            st.info("No customer orders available.")
        else:
            st.metric("Total Orders", len(orders_df))
            delayed_orders = orders_df[
                orders_df["status"].str.lower() == "delayed"
            ]
            st.metric("Delayed Orders", len(delayed_orders))
            st.dataframe(orders_df, use_container_width=True)

    elif page == "Production":
        st.title("Production Monitoring")
        production_df = load_table("production_records")

        if production_df.empty:
            st.info("No production records available.")
        else:
            production_df["production_date"] = pd.to_datetime(
                production_df["production_date"]
            )

            min_date = production_df["production_date"].min().date()
            max_date = production_df["production_date"].max().date()

            selected_dates = st.date_input(
                "Production date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

            if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                start_date, end_date = selected_dates
                filtered_df = production_df[
                    (production_df["production_date"].dt.date >= start_date)
                    & (production_df["production_date"].dt.date <= end_date)
                ]
            else:
                filtered_df = production_df

            planned = filtered_df["planned_quantity"].sum()
            actual = filtered_df["actual_quantity"].sum()
            rejected = filtered_df["rejected_quantity"].sum()
            downtime = filtered_df["downtime_minutes"].sum()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Planned", f"{planned:,.0f}")
            col2.metric("Actual", f"{actual:,.0f}")
            col3.metric("Rejected", f"{rejected:,.0f}")
            col4.metric("Downtime", f"{downtime:,.0f} min")

            chart_data = (
                filtered_df
                .groupby("production_date")[["planned_quantity", "actual_quantity"]]
                .sum()
            )

            st.subheader("Planned vs Actual Production")
            st.line_chart(chart_data)

            st.subheader("Production Records")
            st.dataframe(filtered_df, use_container_width=True)

    elif page == "Inventory":
        st.title("Inventory Management")
        st.dataframe(load_table("inventory"), use_container_width=True)

    elif page == "Maintenance":
        st.title("Maintenance Management")
        st.dataframe(load_table("maintenance_records"), use_container_width=True)

    elif page == "Quality":
        st.title("Quality Management")
        st.dataframe(load_table("quality_inspections"), use_container_width=True)

    elif page == "Workforce":
        st.title("Workforce Management")

        employees_df = load_table("employees")
        attendance_df = load_table("employee_attendance")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Employees", len(employees_df))

        if not attendance_df.empty:
            present_count = len(
                attendance_df[attendance_df["status"].str.lower() == "present"]
            )
            absent_count = len(
                attendance_df[attendance_df["status"].str.lower() == "absent"]
            )
        else:
            present_count = 0
            absent_count = 0

        col2.metric("Present Today", present_count)
        col3.metric("Absent Today", absent_count)

        st.subheader("Employees")

        if employees_df.empty:
            st.info("No employees available.")
        else:
            st.dataframe(employees_df, use_container_width=True)

        st.subheader("Attendance")

        if attendance_df.empty:
            st.info("No attendance records available.")
        else:
            st.dataframe(attendance_df, use_container_width=True)

    elif page == "Purchasing":
        st.title("Purchasing and Suppliers")
        st.dataframe(load_table("purchase_orders"), use_container_width=True)

    elif page == "Costs":
        st.title("Costs and Profitability")
        st.dataframe(load_table("operating_costs"), use_container_width=True)

    elif page == "Safety":
        st.title("Safety and Compliance")
        st.dataframe(load_table("safety_incidents"), use_container_width=True)
except Exception as error:
    st.error(f"Unable to load {page.lower()} data: {error}")
