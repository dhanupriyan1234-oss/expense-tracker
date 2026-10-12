import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Student Expense Analyzer", page_icon="💸", layout="wide")

CATEGORY_RULES = {
    "Food & Snacks": ["food", "snack", "tea", "coffee", "restaurant", "canteen", "bakery", "swiggy", "zomato"],
    "Transport": ["bus", "train", "metro", "petrol", "fuel", "auto", "uber", "ola", "rapido", "travel"],
    "Education": ["book", "college", "course", "exam", "stationery", "print", "xerox", "education"],
    "Bills & Recharge": ["recharge", "mobile", "internet", "wifi", "electricity", "bill"],
    "Shopping": ["shirt", "clothes", "shopping", "amazon", "flipkart", "purchase", "store"],
    "Entertainment": ["movie", "cinema", "game", "music", "netflix", "spotify", "entertainment"],
    "Health": ["medicine", "hospital", "doctor", "pharmacy", "health"],
}

REVIEW_KEYWORDS = ["snack", "coffee", "tea", "movie", "game", "shopping", "netflix", "spotify"]

def categorize(description):
    text = str(description).lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(word in text for word in keywords):
            return category
    return "Other"

def review_reason(description, amount):
    text = str(description).lower()
    if amount >= 1000:
        return "Large transaction — verify that it was planned and necessary"
    if any(word in text for word in REVIEW_KEYWORDS):
        return "Optional purchase — review whether it fits your priorities"
    return "No automatic warning"

def prepare_data(df):
    df = df.copy()
    # Accept common column names
    rename = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ["date", "transaction date", "datetime"]:
            rename[col] = "Date"
        elif c in ["description", "details", "merchant", "transaction", "narration", "name"]:
            rename[col] = "Description"
        elif c in ["amount", "debit", "spent", "value", "transaction amount"]:
            rename[col] = "Amount"
        elif c in ["category", "type"]:
            rename[col] = "Category"
    df = df.rename(columns=rename)
    needed = ["Date", "Description", "Amount"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError("CSV needs columns for Date, Description, and Amount. Found: " + ", ".join(map(str, df.columns)))
    df = df[["Date", "Description", "Amount"]].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Description"] = df["Description"].fillna("Unknown").astype(str)
    df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(",", "").str.replace("₹", "").str.strip(), errors="coerce")
    df = df.dropna(subset=["Date", "Amount"])
    # Expenses should be positive; negative values are converted to absolute values for this demo.
    df["Amount"] = df["Amount"].abs()
    df["Category"] = df["Description"].apply(categorize)
    df["Review note"] = df.apply(lambda r: review_reason(r["Description"], r["Amount"]), axis=1)
    df["Potential review"] = df["Review note"] != "No automatic warning"
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    return df.sort_values("Date", ascending=False)

def sample_data():
    return pd.DataFrame([
        ["2026-10-01", "College bus pass", 450],
        ["2026-10-02", "Canteen snacks", 80],
        ["2026-10-03", "Notebook and stationery", 160],
        ["2026-10-04", "Mobile recharge", 239],
        ["2026-10-05", "Coffee", 90],
        ["2026-10-06", "Bus travel", 60],
        ["2026-10-07", "Online shirt shopping", 799],
        ["2026-10-08", "College books", 500],
        ["2026-10-09", "Movie ticket", 250],
        ["2026-10-10", "Food delivery", 220],
        ["2026-10-11", "Music subscription", 119],
        ["2026-10-12", "Medical pharmacy", 180],
        ["2026-10-12", "Restaurant dinner", 350],
        ["2026-10-12", "Unknown transfer", 1500],
    ], columns=["Date", "Description", "Amount"])

st.title("💸 Student Expense Analyzer & Savings Advisor")
st.caption("Understand where your money goes. Find spending patterns. Make a realistic savings plan.")
with st.sidebar:
    st.header("Your budget")
    budget = st.number_input("Monthly budget (₹)", min_value=0, value=5000, step=500)
    st.write("Upload transaction CSV or use sample data.")
    uploaded = st.file_uploader("Upload CSV file", type=["csv"])
    use_sample = st.button("Load sample transactions", use_container_width=True)
    st.info("Privacy tip: use fictional/sample transactions for demonstrations. Never upload UPI PINs, passwords, or banking credentials.")

if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded)
        data = prepare_data(raw)
        st.success(f"Loaded {len(data)} transactions from your CSV.")
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        st.stop()
elif use_sample or "data" not in st.session_state:
    data = prepare_data(sample_data())
    st.session_state["data"] = data
else:
    data = st.session_state["data"]

if data.empty:
    st.warning("No valid transactions found. Check that dates and amounts are present.")
    st.stop()
st.session_state["data"] = data

total = float(data["Amount"].sum())
remaining = float(budget - total)
review_total = float(data.loc[data["Potential review"], "Amount"].sum())
# Conservative illustrative target: 20% of optional/review transactions, not all flagged spending.
potential_saving = round(review_total * 0.20, 2)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total recorded spending", f"₹{total:,.0f}")
c2.metric("Monthly budget", f"₹{budget:,.0f}")
c3.metric("Budget remaining", f"₹{remaining:,.0f}", delta=f"{(remaining):,.0f} vs budget", delta_color="normal")
c4.metric("Illustrative savings opportunity", f"₹{potential_saving:,.0f}")

if total > budget:
    st.error(f"You are ₹{total-budget:,.0f} over the budget. Review categories and protect essential expenses.")
elif budget > 0 and total >= budget * 0.8:
    st.warning("You have used at least 80% of your budget. Check upcoming essential expenses before spending more.")
else:
    st.success("Recorded spending is currently within the selected budget.")

left, right = st.columns(2)
with left:
    st.subheader("Spending by category")
    category_totals = data.groupby("Category", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False)
    fig = px.pie(category_totals, names="Category", values="Amount", hole=0.45)
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Spending over time")
    daily = data.groupby(data["Date"].dt.date, as_index=False)["Amount"].sum()
    daily.columns = ["Date", "Amount"]
    fig2 = px.bar(daily, x="Date", y="Amount", labels={"Amount": "Spending (₹)"})
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Transactions to review")
review = data[data["Potential review"]].copy()
if review.empty:
    st.write("No transactions were automatically flagged by the simple review rules.")
else:
    st.caption("Flags are prompts to check, not proof that a purchase was wasteful or fraudulent.")
    st.dataframe(review[["Date", "Description", "Amount", "Category", "Review note"]], use_container_width=True, hide_index=True)

st.subheader("Savings recommendations")
recommendations = []
optional = data[data["Description"].str.lower().apply(lambda x: any(k in x for k in REVIEW_KEYWORDS))]
if not optional.empty:
    recommendations.append(f"Review {len(optional)} optional-purchase transaction(s) totalling ₹{optional['Amount'].sum():,.0f}. Choose a realistic limit rather than cutting every purchase.")
if total > budget:
    recommendations.append(f"Recorded spending is ₹{total-budget:,.0f} above budget. Review the largest categories first, without cutting essential travel, education, or healthcare.")
if not optional.empty and optional["Amount"].sum() > 0:
    recommendations.append(f"If you reduce reviewed optional spending by 20%, the illustrative saving would be about ₹{optional['Amount'].sum()*0.2:,.0f}. This is an estimate, not a guarantee.")
large = data[data["Amount"] >= 1000]
if not large.empty:
    recommendations.append(f"Verify {len(large)} transaction(s) of ₹1,000 or more to confirm they are correctly recorded and expected.")
if not recommendations:
    recommendations.append("Keep recording expenses for several weeks so you can compare patterns and set a realistic savings goal.")
for i, rec in enumerate(recommendations, 1):
    st.write(f"{i}. {rec}")

st.subheader("Transaction table")
st.dataframe(data[["Date", "Description", "Amount", "Category", "Review note"]], use_container_width=True, hide_index=True)

csv_bytes = data.drop(columns=["Month"], errors="ignore").to_csv(index=False).encode("utf-8")
st.download_button("Download analyzed transactions as CSV", data=csv_bytes, file_name="analyzed_transactions.csv", mime="text/csv")

with st.expander("How this prototype works"):
    st.markdown("""
    - **Language:** Python
    - **Interface:** Streamlit
    - **Data processing:** Pandas
    - **Charts:** Plotly
    - **Algorithms:** keyword-based transaction categorization, threshold-based large-transaction flags, optional-spending review rules, and arithmetic budget/savings calculations.
    - **Important limitation:** this prototype uses rule-based analysis, not a trained machine-learning model. It cannot directly connect to GPay or a bank; it analyzes a CSV the user provides.
    """)
st.caption("Educational prototype only. Review flagged expenses yourself; a flag does not mean a purchase was unnecessary.")
