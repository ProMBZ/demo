import streamlit as st
import json
import os
import uuid
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from fpdf import FPDF
import pandas as pd

# Load environment variables
load_dotenv()

# Set page config FIRST
st.set_page_config(page_title="RAMAD Perfumes AI Agent", layout="wide")

# Load Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    api_key=os.getenv("GEMINI_API_KEY")
)

# Session state setup
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "mode" not in st.session_state:
    st.session_state.mode = "chatbot"
if "latest_invoice_path" not in st.session_state:
    st.session_state.latest_invoice_path = None
if "latest_order_id" not in st.session_state:
    st.session_state.latest_order_id = None

# Load stock and orders
@st.cache_data
def load_stock():
    with open("stock.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

def save_stock(stock):
    with open("stock.json", "w", encoding="utf-8") as f:
        json.dump({"products": stock}, f, indent=2)

def load_orders():
    if not os.path.exists("orders.json"):
        return []
    with open("orders.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(orders):
    with open("orders.json", "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)

def generate_invoice(order):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="RAMAD Perfumes Invoice", ln=True, align='C')
    pdf.ln(10)
    for k, v in order.items():
        pdf.cell(200, 10, txt=f"{k.capitalize()}: {v}", ln=True)

    invoice_path = f"invoices/invoice_{order['id']}.pdf"
    os.makedirs("invoices", exist_ok=True)
    pdf.output(invoice_path)
    return invoice_path

# Mode selector
mode = st.sidebar.selectbox("Choose Mode", ["User Chatbot", "Admin Dashboard"])
st.session_state.mode = "admin" if mode == "Admin Dashboard" else "chatbot"

# USER CHATBOT
if st.session_state.mode == "chatbot":
    st.title("🤖 RAMAD Perfumes AI Chat Agent")
    user_input = st.text_area("💬 Ask me anything about perfumes:")

    if st.button("💡 Get Answer") and user_input:
        is_arabic = "arabic" in user_input.lower() or "عربي" in user_input
        stock = load_stock()

        stock_list = "\n".join([f"{p['name']} ({p['category']}, {p['size']}, AED {p['price']}, In Stock: {p['stock']})" for p in stock])

        prompt = f"You are an expert fragrance assistant for RAMAD Perfumes. Respond {'in Arabic' if is_arabic else 'in English'} to this user query: '{user_input}'.\nHere is our current perfume stock:\n{stock_list}"

        with st.spinner("Thinking..."):
            try:
                response = llm.invoke(prompt)
                st.success("AI Response")
                st.markdown(response.content)
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()
    st.subheader("📦 Place an Order")
    with st.form("order_form"):
        name = st.text_input("Your Name")
        address = st.text_input("Address")
        location = st.text_input("Optional Location Pin")
        product = st.selectbox("Choose Perfume", [p['name'] for p in load_stock()])
        quantity = st.number_input("Quantity", min_value=1, step=1)
        submit = st.form_submit_button("🛒 Place Order")

        if submit:
            stock = load_stock()
            selected = next((item for item in stock if item['name'] == product), None)

            if selected and selected['stock'] >= quantity:
                order_id = str(uuid.uuid4())[:8]
                total = selected['price'] * quantity

                selected['stock'] -= quantity
                save_stock(stock)

                orders = load_orders()
                new_order = {
                    "id": order_id,
                    "name": name,
                    "address": address,
                    "location": location,
                    "product": product,
                    "quantity": quantity,
                    "total": total,
                    "status": "Pending"
                }
                orders.append(new_order)
                save_orders(orders)

                invoice_path = generate_invoice(new_order)
                st.session_state.latest_invoice_path = invoice_path
                st.session_state.latest_order_id = order_id

                st.success(f"✅ Order placed! Your order ID is {order_id}")
            else:
                st.error("❌ Not enough stock available.")

    if st.session_state.latest_invoice_path:
        st.download_button("📄 Download Invoice", data=open(st.session_state.latest_invoice_path, "rb").read(), file_name=os.path.basename(st.session_state.latest_invoice_path))

    st.subheader("📦 Track Your Order")
    check_id = st.text_input("Enter your Order ID")
    if st.button("🔍 Track Order") and check_id:
        orders = load_orders()
        found = next((o for o in orders if o['id'] == check_id), None)
        if found:
            st.info(f"🧾 Order Status: {found['status']}")
        else:
            st.warning("Order ID not found.")

# ADMIN DASHBOARD
elif st.session_state.mode == "admin":
    if not st.session_state.authenticated:
        st.title("🔐 Admin Login")
        password = st.text_input("Enter admin password", type="password")
        if password == "perfumes":
            st.session_state.authenticated = True
            st.experimental_rerun()
        else:
            st.stop()

    st.title("🌟 RAMAD Perfumes Admin Dashboard")
    tabs = st.tabs(["📦 Stock", "🧾 Orders", "📊 Analytics", "🤖 AI Chat Agent"])

    # STOCK TAB
    with tabs[0]:
        st.header("📦 Current Stock")
        stock = load_stock()

        for i, item in enumerate(stock):
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 1, 1, 1])
            col1.markdown(f"**{item['name']}**")
            col2.write(item['category'])
            col3.write(item['size'])
            col4.write(f"AED {item['price']}")
            col5.write(f"🧮 {item['stock']}")
            new_stock = col6.number_input(f"Update Stock", value=item['stock'], key=f"stk_{i}")
            if new_stock != item['stock']:
                item['stock'] = new_stock
                save_stock(stock)
                st.success("✅ Stock updated")

    # ORDERS TAB
    with tabs[1]:
        st.header("🧾 Customer Orders")
        orders = load_orders()

        if not orders:
            st.info("No orders yet.")
        else:
            for i, order in enumerate(reversed(orders)):
                with st.expander(f"📦 Order ID: {order['id']}"):
                    st.write(f"**Name:** {order['name']}")
                    st.write(f"**Address:** {order['address']}")
                    st.write(f"**Product:** {order['product']}")
                    st.write(f"**Quantity:** {order['quantity']}")
                    st.write(f"**Total:** AED {order['total']}")
                    st.write(f"**Status:** {order['status']}")
                    if order.get("location"):
                        st.write(f"**Location Pin:** {order['location']}")

                    new_status = st.selectbox("Update Status", ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"], index=["Pending", "Processing", "Shipped", "Delivered", "Cancelled"].index(order["status"]), key=f"status_{order['id']}")
                    if new_status != order['status']:
                        order['status'] = new_status
                        save_orders(orders)
                        st.success("✅ Status updated")

    # ANALYTICS TAB
    with tabs[2]:
        st.header("📊 Dashboard Analytics")
        orders = load_orders()
        if orders:
            df = pd.DataFrame(orders)
            st.metric("Total Orders", len(df))
            st.metric("Total Revenue (AED)", df['total'].sum())
            st.bar_chart(df['status'].value_counts())
        else:
            st.info("No data to show.")

    # AI CHAT TAB FOR ADMIN
    with tabs[3]:
        st.header("🤖 AI Agent Test")
        user_input = st.text_area("💬 Ask something for testing:")

        if st.button("🧪 Test Response") and user_input:
            stock = load_stock()
            stock_list = "\n".join([f"{p['name']} ({p['category']}, {p['size']}, AED {p['price']}, In Stock: {p['stock']})" for p in stock])

            prompt = f"Admin test mode: respond to '{user_input}' with knowledge of current stock:\n{stock_list}"
            with st.spinner("Thinking..."):
                try:
                    response = llm.invoke(prompt)
                    st.success("AI Response")
                    st.markdown(response.content)
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # Logout
    if st.button("🔓 Logout"):
        st.session_state.authenticated = False
        st.rerun()
