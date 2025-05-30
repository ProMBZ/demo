import streamlit as st
import json
import os

# Load Stock and Orders
def load_stock():
    with open("stock.json", "r") as f:
        return json.load(f)["products"]

def load_orders():
    if not os.path.exists("orders.json"):
        return []
    with open("orders.json", "r") as f:
        return json.load(f)

# Save Order
def save_orders(orders):
    with open("orders.json", "w") as f:
        json.dump(orders, f, indent=2)

# Password Protection
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.set_page_config(page_title="Perfume Admin Login")
    st.title("🔐 Admin Login")
    password = st.text_input("Enter admin password", type="password")
    if password == "perfumes":
        st.session_state.authenticated = True
        st.experimental_rerun()
    else:
        st.stop()

# Admin Dashboard UI
st.set_page_config(page_title="Perfume Admin", layout="wide")
st.title("🌟 RAMAD Perfumes Admin Dashboard")

# Tabs
tabs = st.tabs(["📦 Stock", "🧾 Orders"])

# --- STOCK TAB ---
with tabs[0]:
    st.header("📦 Current Stock")
    stock = load_stock()
    st.markdown("""
    <style>
    .element-container:has(.stColumns) {
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

    for item in stock:
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
        col1.markdown(f"**{item['name']}**")
        col2.write(item['category'])
        col3.write(item['size'])
        col4.write(f"AED {item['price']}")
        col5.write(f"🧮 {item['stock']}")

# --- ORDERS TAB ---
with tabs[1]:
    st.header("🧾 Customer Orders")
    orders = load_orders()

    if len(orders) == 0:
        st.info("No orders yet.")
    else:
        for i, order in enumerate(orders[::-1]):  # reverse chronological
            with st.expander(f"📦 Order #{len(orders)-i}"):
                st.write(f"**Name:** {order['name']}")
                st.write(f"**Address:** {order['address']}")
                st.write(f"**Product:** {order['product']}")
                st.write(f"**Quantity:** {order['quantity']}")
                st.write(f"**Total:** AED {order['total']}")
                if order.get("location"):
                    st.write(f"**Location Pin:** {order['location']}")

# Logout option
if st.button("🔓 Logout"):
    st.session_state.authenticated = False
    st.experimental_rerun()
