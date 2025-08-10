# frontend/main.py
import streamlit as st
import requests
import json
from typing import Optional, Dict, List

# Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'feature_flags' not in st.session_state:
    st.session_state.feature_flags = {}

# Helper Functions
# Add this near your other helper functions
def get_feature_flags():
    """Fetch feature flags from backend"""
    if 'feature_flags' not in st.session_state:
        flags = make_api_request("/feature-flags")
        st.session_state.feature_flags = flags if flags else {}
    return st.session_state.feature_flags



def make_api_request(endpoint: str, method: str = "GET", data: Dict = None, auth_required: bool = False) -> Optional[Dict]:
    """Make API request to FastAPI backend"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if auth_required and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")
        return None

def logout():
    """Clear session state and log out user"""
    st.session_state.token = None
    st.session_state.user_info = None
    st.rerun()

def check_auth():
    """Check if user is authenticated and get user info"""
    if st.session_state.token:
        user_info = make_api_request("/me", auth_required=True)
        if user_info:
            st.session_state.user_info = user_info
            return True
        else:
            # Token is invalid, clear it
            st.session_state.token = None
            st.session_state.user_info = None
    return False

# Page Functions
def show_login_page():
    """Display login/register page"""
    st.title("📚 Book Subscription Platform")
    st.write("Welcome! Please login or create an account to continue.")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if email and password:
                    response = make_api_request("/login", "POST", {
                        "email": email,
                        "password": password
                    })
                    
                    if response:
                        st.session_state.token = response["access_token"]
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
                else:
                    st.error("Please fill in all fields.")
    
    with tab2:
        st.subheader("Create Account")
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password")
            register_button = st.form_submit_button("Create Account")
            
            if register_button:
                if reg_email and reg_password and reg_confirm_password:
                    if reg_password != reg_confirm_password:
                        st.error("Passwords don't match!")
                    else:
                        response = make_api_request("/register", "POST", {
                            "email": reg_email,
                            "password": reg_password
                        })
                        
                        if response:
                            st.success("Account created successfully! Please login.")
                        else:
                            st.error("Registration failed. Email might already be in use.")
                else:
                    st.error("Please fill in all fields.")

def show_dashboard():
    """Display user dashboard"""
    st.title("📚 Your Dashboard")
    
    # User info sidebar
    with st.sidebar:
        st.write(f"**Welcome, {st.session_state.user_info['email']}!**")
        st.write(f"**Plan:** {st.session_state.user_info['subscription_plan'].title()}")
        
        if st.button("Logout", use_container_width=True):
            logout()
    
    # Main dashboard content
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📖 Books in Library", get_user_books_count())
    
    with col2:
        st.metric("💎 Current Plan", st.session_state.user_info['subscription_plan'].title())
    
    with col3:
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.rerun()

def show_browse_books():
    """Display book browsing page"""
    st.title("📚 Browse Books")
    
    # Get feature flags
    flags = get_feature_flags()
    
    # Show discount banner for free users
    if (flags.get('discount_type') == '20_off_first_month' and 
        st.session_state.user_info['subscription_plan'] == 'free'):
        st.info("🎉 **Special Offer:** Get 20% off your first month of Premium! [Upgrade Now](/subscription)")
    
    # Show urgency message for free users
    if flags.get('urgency_message') == 'enabled' and st.session_state.user_info['subscription_plan'] == 'free':
        st.warning("⏰ **Limited Time:** Upgrade to Premium within 24 hours to access all premium books!")
    
    
    # Get all books
    books = make_api_request("/books", auth_required=True)
    
    if books:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            genre_filter = st.selectbox("Filter by Genre", 
                                      ["All"] + list(set([book['genre'] for book in books])))
        with col2:
            show_premium_only = st.checkbox("Premium Books Only")
        
        # Filter books
        filtered_books = books
        if genre_filter != "All":
            filtered_books = [book for book in filtered_books if book['genre'] == genre_filter]
        if show_premium_only:
            filtered_books = [book for book in filtered_books if book['is_premium']]
        
        # Display books in grid
        for i in range(0, len(filtered_books), 2):
            col1, col2 = st.columns(2)
            
            # First book
            with col1:
                if i < len(filtered_books):
                    display_book_card(filtered_books[i])
            
            # Second book
            with col2:
                if i + 1 < len(filtered_books):
                    display_book_card(filtered_books[i + 1])
    else:
        st.error("Failed to load books. Please try again.")

def display_book_card(book: Dict):
    """Display individual book card"""
    with st.container():
        st.markdown("---")
        
        # Book header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(book['title'])
            st.write(f"**Author:** {book['author']}")
            st.write(f"**Genre:** {book['genre']}")
            if book['is_premium']:
                st.write("💎 **Premium Book**")
        
        with col2:
            st.write(f"**${book['price']:.2f}**")
        
        # Description
        st.write(book['description'])
        
        # Add to library button
        if st.button(f"Add to Library", key=f"add_{book['id']}", use_container_width=True):
            response = make_api_request(f"/books/{book['id']}/add-to-library", "POST", auth_required=True)
            if response:
                st.success("Book added to your library!")
                st.rerun()
            else:
                if book['is_premium'] and st.session_state.user_info['subscription_plan'] == 'free':
                    st.error("Premium subscription required for this book!")
                else:
                    st.error("Failed to add book. You might already have it.")

def show_my_library():
    """Display user's book library"""
    st.title("📖 My Library")
    
    # Get user's books
    user_books = make_api_request("/my-books", auth_required=True)
    
    if user_books:
        if len(user_books) == 0:
            st.info("Your library is empty. Go browse some books!")
            if st.button("Browse Books"):
                st.session_state.page = "browse"
                st.rerun()
        else:
            st.write(f"You have {len(user_books)} books in your library.")
            
            # Display user's books
            for book in user_books:
                with st.container():
                    st.markdown("---")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**{book['title']}**")
                        st.write(f"by {book['author']}")
                    
                    with col2:
                        st.write(f"Genre: {book['genre']}")
                        if book['is_premium']:
                            st.write("💎 Premium")
                    
                    with col3:
                        if st.button("Mark as Read", key=f"read_{book['id']}"):
                            response = make_api_request(f"/books/{book['id']}/mark-read", "POST", auth_required=True)
                            if response:
                                st.success("Marked as read!")
                                st.rerun()
    else:
        st.error("Failed to load your library.")

def show_subscription_page():
    """Display subscription management page"""
    st.title("💎 Subscription Plans")

    flags = get_feature_flags()
    
    current_plan = st.session_state.user_info['subscription_plan']
    st.write(f"**Current Plan:** {current_plan.title()}")

    if flags.get('urgency_message') == 'enabled' and current_plan == 'free':
        st.warning("⏰ **Limited Time Offer!** Upgrade your plan within the next 24 hours to get premium access!")

    # A/B Test: Discount messaging
    discount_message = ""
    if flags.get('discount_type') == '20_off_first_month':
        discount_message = "🎉 **20% OFF** your first month!"
        st.success(discount_message)
    
    # Get subscription plans
    plans = make_api_request("/subscription-plans", auth_required=True)
    
    if plans:
        st.write("Choose your subscription plan:")

        # A/B Test: Plan ordering
        if flags.get('plan_order') == 'premium_first':
            # Show premium plans first
            plans = sorted(plans, key=lambda x: x['price'], reverse=True)
        else:
            # Show basic plans first (default: basic_first or any other value)
            plans = sorted(plans, key=lambda x: x['price'])

        
        for plan in plans:
            with st.container():
                st.markdown("---")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.subheader(plan['name'].title())
                    # Highlight premium plans if premium_first flag is true
                    if flags.get('plan_order') == 'premium_first' and plan['price'] > 0:
                        st.subheader(f"⭐ {plan_title} (Recommended)")
                    else:
                        st.subheader(plan_title)
                    st.write(plan['description'])
                    st.write(f"Max books: {plan['max_books']}")
                
                with col2:
                    if plan['price'] == 0:
                        st.write("**FREE**")
                    else:
                        # Show discounted price if discount flag is active
                        if flags.get('discount_type') == '20_off_first_month' and current_plan == 'free':
                            original_price = plan['price']
                            discounted_price = original_price * 0.8
                            st.write(f"~~${original_price:.2f}~~ **${discounted_price:.2f}**/month")
                            st.caption("First month only")
                        else:
                            st.write(f"**${plan['price']:.2f}/month**")
                        
                
                with col3:
                    if current_plan == plan['name']:
                        st.success("Current Plan")
                    else:
                        # Dynamic button text based on flags
                        button_text = "Subscribe"
                        if flags.get('urgency_message') == 'enabled' and plan['price'] > 0:
                            button_text = "Upgrade Now!"
                        if flags.get('discount_type') == '20_off_first_month' and plan['price'] > 0 and current_plan == 'free':
                            button_text = "Get 20% Off!"
                        
                        if st.button(button_text, key=f"sub_{plan['id']}"):
                            response = make_api_request(f"/subscribe/{plan['id']}", "POST", auth_required=True)
                            if response:
                                st.success(f"Subscribed to {plan['name']} plan!")
                                st.session_state.user_info['subscription_plan'] = plan['name']
                                st.rerun()
                            else:
                                st.error("Subscription failed. Please try again.")
    else:
        st.error("Failed to load subscription plans.")

def get_user_books_count() -> int:
    """Get count of books in user's library"""
    user_books = make_api_request("/my-books", auth_required=True)
    return len(user_books) if user_books else 0

# Main App
def main():
    st.set_page_config(
        page_title="Book Subscription Platform",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'
    
    # Check authentication
    if not check_auth():
        show_login_page()
        return
    
    # Navigation
    with st.sidebar:
        st.title("Navigation")
        pages = {
            "Dashboard": "dashboard",
            "Browse Books": "browse",
            "My Library": "library",
            "Subscription": "subscription"
        }
        
        for page_name, page_key in pages.items():
            if st.button(page_name, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.page = page_key
                st.rerun()
    
    # Display selected page
    if st.session_state.page == 'dashboard':
        show_dashboard()
    elif st.session_state.page == 'browse':
        show_browse_books()
    elif st.session_state.page == 'library':
        show_my_library()
    elif st.session_state.page == 'subscription':
        show_subscription_page()

if __name__ == "__main__":

    main()
