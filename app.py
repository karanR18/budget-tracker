import streamlit as st
import pandas as pd
import database
import altair as alt
from datetime import datetime, timedelta

# Load data
df = database.load_data()

expected_columns = ["Date", "Category", "Amount", "Note", "Type"]
for col in expected_columns:
    if col not in df.columns:
        df[col] = pd.NA

# Clean dates
df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")
df = df.dropna(subset=["Date"])
df["Month"] = df["Date"].dt.to_period("M")

# Streamlit settings
st.set_page_config(page_title="💸 Budget Tracker", layout="centered", initial_sidebar_state="collapsed")

# Hide Streamlit's default UI
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Page Title
st.title("💹 Personal Budget Tracker")

# Predefined + past categories
default_income_categories = ["Salary", "Freelance", "Business", "Interest", "Investments", "Gifts", "Other"]
default_expense_categories = ["Rent", "Groceries", "Bills", "Travel", "Education", "Entertainment",
                              "Medical", "Shopping", "Subscriptions", "Dining Out", "Fuel", "Other"]

past_income_cats = df[df["Type"] == "Income"]["Category"].dropna().unique().tolist()
past_expense_cats = df[df["Type"] == "Expense"]["Category"].dropna().unique().tolist()

income_categories = sorted(set(default_income_categories + past_income_cats))
expense_categories = sorted(set(default_expense_categories + past_expense_cats))

# ───────────────────────────────
# 📦 Add Transaction Form
# ───────────────────────────────
with st.expander("➕➖ Add a Transaction", expanded=True):
    with st.form("transaction_form", clear_on_submit=True):
        st.markdown("### 📝 Transaction Details")

        col1, col2 = st.columns(2)
        with col1:
            txn_type = st.radio("Type", ["Income", "Expense"], horizontal=True)
            amount = st.number_input("Amount", min_value=0.01, step=1.0)
        with col2:
            category = st.selectbox(
                "Category",
                income_categories if txn_type == "Income" else expense_categories
            )
            note = st.text_input("Note", placeholder="e.g., Grocery shopping")

        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            submitted = st.form_submit_button("💾 Add Transaction")

        if submitted:
            signed_amount = amount if txn_type == "Income" else -amount
            new_entry = {
                "Date": pd.Timestamp.now().date(),
                "Category": category,
                "Amount": signed_amount,
                "Note": note,
                "Type": txn_type
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            database.save_data(df)

            st.success(f"{'✅ Income' if txn_type == 'Income' else '💸 Expense'} added!")

# ───────────────────────────────
# 📊 Balance + History
# ───────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Balance Summary")
    total_income = df[df["Amount"] > 0]["Amount"].sum()
    total_expense = df[df["Amount"] < 0]["Amount"].sum()
    balance = total_income + total_expense
    st.metric("Current Balance", f"₹ {balance:.2f}")
    st.metric("Total Income", f"₹ {total_income:.2f}")
    st.metric("Total Expenses", f"₹ {abs(total_expense):.2f}")

with col2:
    st.subheader("📜 Transaction History")
    if st.button("Show All Transactions"):
        st.dataframe(df[::-1], use_container_width=True)

# ───────────────────────────────
# 📈 Expense Stats by Category
# ───────────────────────────────
st.markdown("---")
st.subheader("📈 Expense Stats by Category")

if not df.empty:
    expense_data = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
    if not expense_data.empty:
        st.bar_chart(expense_data)

# ───────────────────────────────
# 📅 Daily Grouped Bar Chart
# ───────────────────────────────
st.subheader("📅 Daily Income & Expense (Current Month)")

# Get current month date range
today = pd.Timestamp.now().date()
start_of_month = today.replace(day=1)
end_of_month = (start_of_month + pd.offsets.MonthEnd(1)).date()
all_days = pd.date_range(start=start_of_month, end=end_of_month)

# Create base DataFrame for full month
full_range_df = pd.DataFrame({
    "Date": all_days
})
full_range_df["DayLabel"] = full_range_df["Date"].dt.strftime("%a - %d %b")

# Prepare transaction data
chart_df = df.copy()
chart_df["Date"] = pd.to_datetime(chart_df["Date"])
chart_df["Amount"] = chart_df["Amount"].abs()
chart_df = chart_df[(chart_df["Date"].dt.date >= start_of_month) & (chart_df["Date"].dt.date <= end_of_month)]

# Group by Date and Type
grouped = chart_df.groupby([chart_df["Date"].dt.date, "Type"])["Amount"].sum().unstack().fillna(0)
grouped["Date"] = grouped.index
grouped["DayLabel"] = pd.to_datetime(grouped["Date"]).dt.strftime("%a - %d %b")

# Merge with full month to fill gaps
final_chart_data = pd.merge(full_range_df, grouped, on=["DayLabel"], how="left").fillna(0)

# Melt to long format for Altair
melted = final_chart_data.melt(id_vars=["DayLabel"], value_vars=["Income", "Expense"],
                               var_name="Type", value_name="Amount")

# Grouped side-by-side bars using xOffset
bar_chart = alt.Chart(melted).mark_bar().encode(
    x=alt.X("DayLabel:N", title="Date", sort=final_chart_data["DayLabel"].tolist()),
    y=alt.Y("Amount:Q", title="Amount (₹)"),
    color=alt.Color("Type:N",
        scale=alt.Scale(
            domain=["Income", "Expense"],
            range=["#4CAF50", "#E53935"]  # Green and Red
        ),
        legend=alt.Legend(title="Transaction Type")
    ),
    xOffset="Type:N",
    tooltip=["Type", "Amount", "DayLabel"]
).properties(
    width="container",
    height=400
).configure_axisX(
    labelAngle=-45
)


st.altair_chart(bar_chart, use_container_width=True)


# ───────────────────────────────
# ⚙️ Options
# ───────────────────────────────
st.markdown("### ⚙️ Options")
col_dl, col_clear = st.columns(2)

with col_dl:
    st.download_button(
        label="⬇️ Download CSV",
        data=df.to_csv(index=False),
        file_name="transactions.csv",
        mime="text/csv"
    )

with col_clear:
    if st.button("❌ Clear All Data"):
        database.reset_data()
        df = database.load_data()
        st.warning("All data cleared.")
