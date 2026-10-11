
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

# LOGIN AND REGISTRATION
if st.session_state.user:
    st.success(f"Logged in as {st.session_state.user}")
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()
else:
    action = st.radio("Account", ["Login", "Register"], horizontal=True)
    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password")

    if st.button(action):
        if not username or not password:
            st.error("Enter both username and password.")
        else:
            try:
                with get_db() as conn:
                    if action == "Register":
                        conn.execute(
                            """INSERT INTO users (username, password_hash)
                               VALUES (%s, %s)""",
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
            except Exception as e:
                st.error(f"Account error: {e}")

st.divider()
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

    if not products:
        st.info("No products found.")

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
                    value=float(highest) + 100.0,
                    step=50.0,
                    key=f"bid_{pid}"
                )

                if st.button("Place bid", key=f"place_{pid}"):
                    try:
                        with get_db() as conn:
                            # Lock the product row while checking and inserting.
                            product = conn.execute("""
                                SELECT starting_price
                                FROM products
                                WHERE product_id = %s
                                FOR UPDATE
                            """, (pid,)).fetchone()

                            if not product:
                                st.error("Product not found.")
                            else:
                                latest = conn.execute("""
                                    SELECT MAX(bid_amount)
                                    FROM bids
                                    WHERE product_id = %s
                                """, (pid,)).fetchone()[0]

                                current = max(
                                    float(product[0]),
                                    float(latest) if latest is not None else 0.0
                                )

                                if amount <= current:
                                    st.error(
                                        f"Bid must exceed ₹{current:.2f}."
                                    )
                                else:
                                    user_row = conn.execute(
                                        "SELECT user_id FROM users WHERE username = %s",
                                        (st.session_state.user,)
                                    ).fetchone()

                                    if not user_row:
                                        st.error("User account not found.")
                                    else:
                                        conn.execute("""
                                            INSERT INTO bids
                                                (user_id, product_id, bid_amount)
                                            VALUES (%s, %s, %s)
                                        """, (user_row[0], pid, amount))

                                        st.success("Bid placed successfully!")
                                        st.rerun()

                    except Exception as e:
                        st.error(f"Bid failed: {e}")

except Exception as e:
    st.error(f"Product/database error: {e}")
