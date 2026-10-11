
import streamlit as st
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash

st.set_page_config(page_title="Online Auction System", page_icon="🔨")
st.title("🔨 Online Auction System")
st.write("Register, explore products, and place bids.")

def get_db():
    return psycopg.connect(**st.secrets["db"])

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user:
    st.success(f"Logged in as {st.session_state.user}")
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()
else:
    action = st.radio("Account", ["Login", "Register"], horizontal=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button(action):
        try:
            with get_db() as conn:
                if action == "Register":
                    conn.execute(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (username, generate_password_hash(password))
                    )
                    st.success("Account created. Please log in.")
                else:
                    row = conn.execute(
                        "SELECT password_hash FROM users WHERE username = %s",
                        (username,)
                    ).fetchone()
                    if row and check_password_hash(row[0], password):
                        st.session_state.user = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
        except Exception:
            st.error("Could not complete the request. Check the database settings or username.")

st.subheader("Available Products")

try:
    with get_db() as conn:
        products = conn.execute("""
            SELECT p.product_id, p.product_name, p.description,
                   p.starting_price,
                   COALESCE(MAX(b.bid_amount), p.starting_price) AS highest
            FROM products p
            LEFT JOIN bids b ON p.product_id = b.product_id
            GROUP BY p.product_id
            ORDER BY p.product_id
        """).fetchall()

    for pid, name, description, price, highest in products:
        with st.container(border=True):
            st.subheader(name)
            st.write(description or "")
            st.write(f"Starting price: ₹{price}")
            st.write(f"Current highest bid: ₹{highest}")

            if st.session_state.user:
                amount = st.number_input(
                    f"Your bid for {name} (₹)",
                    min_value=0.0,
                    value=float(highest) + 100,
                    step=50.0,
                    key=f"bid_{pid}"
                )
                if st.button(f"Place bid — {name}", key=f"place_{pid}"):
                    try:
                        with get_db() as conn:
                            current = conn.execute("""
                                SELECT GREATEST(
                                    p.starting_price,
                                    COALESCE(MAX(b.bid_amount), 0)
                                )
                                FROM products p
                                LEFT JOIN bids b ON p.product_id = b.product_id
                                WHERE p.product_id = %s
                                GROUP BY p.product_id
                            """, (pid,)).fetchone()[0]

                            if amount <= float(current):
                                st.error("Your bid must exceed the current highest bid.")
                            else:
                                uid = conn.execute(
                                    "SELECT user_id FROM users WHERE username = %s",
                                    (st.session_state.user,)
                                ).fetchone()[0]
                                conn.execute("""
                                    INSERT INTO bids (user_id, product_id, bid_amount)
                                    VALUES (%s, %s, %s)
                                """, (uid, pid, amount))
                                st.success("Bid placed successfully!")
                                st.rerun()
                    except Exception:
                        st.error("Could not place the bid. Please try again.")
except Exception:
    st.warning("Connect the Supabase database to display products.")
