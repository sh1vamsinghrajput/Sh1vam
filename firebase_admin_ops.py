"""
SMM PANEL - FIREBASE ADMIN MODULE
This module handles all Firestore operations
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ================================================
# FIREBASE INITIALIZATION
# ================================================

# Initialize Firebase Admin SDK
# Make sure to set the FIREBASE_CREDENTIALS_PATH environment variable
cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

if not os.path.exists(cred_path):
    raise FileNotFoundError(f"Firebase credentials file not found at {cred_path}")

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

# Get Firestore database reference
db = firestore.client()

# ================================================
# COLLECTIONS
# ================================================

USERS_COLLECTION = 'users'
ORDERS_COLLECTION = 'orders'

# ================================================
# USER OPERATIONS
# ================================================

def create_user(uid: str, email: str) -> bool:
    """Create a new user document"""
    try:
        user_ref = db.collection(USERS_COLLECTION).document(uid)
        user_ref.set({
            'email': email,
            'username': None,
            'balance': 0,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def get_user(uid: str) -> dict:
    """Get user data by UID"""
    try:
        user_ref = db.collection(USERS_COLLECTION).document(uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            return user_doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def set_user_username(uid: str, username: str) -> bool:
    """Set username for user (one-time only)"""
    try:
        user = get_user(uid)
        if not user:
            raise ValueError("User not found")
        
        if user.get('username'):
            raise ValueError("Username already set. Cannot change.")
        
        user_ref = db.collection(USERS_COLLECTION).document(uid)
        user_ref.update({
            'username': username,
            'updated_at': datetime.now()
        })
        return True
    except Exception as e:
        print(f"Error setting username: {e}")
        return False

def get_user_balance(uid: str) -> float:
    """Get user balance"""
    try:
        user = get_user(uid)
        if user:
            return user.get('balance', 0)
        return 0
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0

def update_user_balance(uid: str, data: dict) -> bool:
    """Update any user field"""
    try:
        user_ref = db.collection(USERS_COLLECTION).document(uid)
        data['updated_at'] = datetime.now()
        user_ref.update(data)
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False

def set_balance(uid: str, amount: float) -> bool:
    """Set balance to specific amount"""
    try:
        return update_user_balance(uid, {'balance': amount})
    except Exception as e:
        print(f"Error setting balance: {e}")
        return False

def add_balance_to_user(uid: str, amount: float) -> bool:
    """Add amount to user balance"""
    try:
        current_balance = get_user_balance(uid)
        new_balance = current_balance + amount
        return set_balance(uid, new_balance)
    except Exception as e:
        print(f"Error adding balance: {e}")
        return False

def deduct_user_balance(uid: str, amount: float) -> bool:
    """Deduct amount from user balance"""
    try:
        current_balance = get_user_balance(uid)
        if current_balance < amount:
            raise ValueError("Insufficient balance")
        new_balance = current_balance - amount
        return set_balance(uid, new_balance)
    except Exception as e:
        print(f"Error deducting balance: {e}")
        return False

def get_all_users() -> list:
    """Get all users"""
    try:
        users = []
        docs = db.collection(USERS_COLLECTION).stream()
        for doc in docs:
            user_data = doc.to_dict()
            user_data['uid'] = doc.id
            users.append(user_data)
        return users
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []

# ================================================
# ORDER OPERATIONS
# ================================================

def save_order(order_data: dict) -> str:
    """Save a new order and return order ID"""
    try:
        order_data['created_at'] = datetime.now()
        order_data['updated_at'] = datetime.now()
        
        # Add document to orders collection
        doc_ref = db.collection(ORDERS_COLLECTION).add(order_data)
        order_id = doc_ref[1].id
        
        return order_id
    except Exception as e:
        print(f"Error saving order: {e}")
        raise

def get_order(order_id: str) -> dict:
    """Get order by ID"""
    try:
        order_ref = db.collection(ORDERS_COLLECTION).document(order_id)
        order_doc = order_ref.get()
        if order_doc.exists:
            order_data = order_doc.to_dict()
            order_data['id'] = order_id
            return order_data
        return None
    except Exception as e:
        print(f"Error getting order: {e}")
        return None

def get_user_orders(uid: str) -> list:
    """Get all orders for a specific user"""
    try:
        orders = []
        docs = db.collection(ORDERS_COLLECTION)\
               .where('uid', '==', uid)\
               .order_by('created_at', direction=firestore.Query.DESCENDING)\
               .stream()
        
        for doc in docs:
            order_data = doc.to_dict()
            order_data['id'] = doc.id
            orders.append(order_data)
        
        return orders
    except Exception as e:
        print(f"Error getting user orders: {e}")
        return []

def get_all_orders(status: str = None) -> list:
    """Get all orders, optionally filtered by status"""
    try:
        orders = []
        
        if status:
            docs = db.collection(ORDERS_COLLECTION)\
                   .where('status', '==', status)\
                   .order_by('created_at', direction=firestore.Query.DESCENDING)\
                   .stream()
        else:
            docs = db.collection(ORDERS_COLLECTION)\
                   .order_by('created_at', direction=firestore.Query.DESCENDING)\
                   .stream()
        
        for doc in docs:
            order_data = doc.to_dict()
            order_data['id'] = doc.id
            orders.append(order_data)
        
        return orders
    except Exception as e:
        print(f"Error getting all orders: {e}")
        return []

def update_order_status(order_id: str, status: str) -> bool:
    """Update order status"""
    try:
        order_ref = db.collection(ORDERS_COLLECTION).document(order_id)
        order_ref.update({
            'status': status,
            'updated_at': datetime.now()
        })
        return True
    except Exception as e:
        print(f"Error updating order: {e}")
        return False

def get_pending_orders() -> list:
    """Get all pending orders"""
    return get_all_orders(status='pending')

def get_completed_orders() -> list:
    """Get all completed orders"""
    return get_all_orders(status='completed')

# ================================================
# STATISTICS
# ================================================

def get_order_stats() -> dict:
    """Get order statistics"""
    try:
        all_orders = get_all_orders()
        pending = [o for o in all_orders if o.get('status') == 'pending']
        completed = [o for o in all_orders if o.get('status') == 'completed']
        
        total_revenue = sum(o.get('amount', 0) for o in all_orders)
        
        return {
            'total_orders': len(all_orders),
            'pending_orders': len(pending),
            'completed_orders': len(completed),
            'total_revenue': total_revenue
        }
    except Exception as e:
        print(f"Error getting order stats: {e}")
        return {}

def get_user_stats() -> dict:
    """Get user statistics"""
    try:
        all_users = get_all_users()
        total_balance = sum(u.get('balance', 0) for u in all_users)
        
        return {
            'total_users': len(all_users),
            'total_balance': total_balance
        }
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {}

# ================================================
# BATCH OPERATIONS
# ================================================

def transfer_balance(from_uid: str, to_uid: str, amount: float) -> bool:
    """Transfer balance from one user to another"""
    try:
        if deduct_user_balance(from_uid, amount):
            if add_balance_to_user(to_uid, amount):
                return True
        return False
    except Exception as e:
        print(f"Error transferring balance: {e}")
        return False

def bulk_add_balance(uid_list: list, amount: float) -> dict:
    """Add balance to multiple users"""
    try:
        results = {}
        for uid in uid_list:
            results[uid] = add_balance_to_user(uid, amount)
        return results
    except Exception as e:
        print(f"Error bulk adding balance: {e}")
        return {}

# ================================================
# DATA VERIFICATION
# ================================================

def verify_user_data(uid: str) -> dict:
    """Verify user data integrity"""
    try:
        user = get_user(uid)
        if not user:
            return {'valid': False, 'error': 'User not found'}
        
        issues = []
        
        if not user.get('email'):
            issues.append('Missing email')
        if user.get('balance') is None:
            issues.append('Missing balance')
        if 'created_at' not in user:
            issues.append('Missing created_at')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'user': user
        }
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def verify_order_data(order_id: str) -> dict:
    """Verify order data integrity"""
    try:
        order = get_order(order_id)
        if not order:
            return {'valid': False, 'error': 'Order not found'}
        
        issues = []
        
        required_fields = ['uid', 'username', 'service', 'amount', 'quantity', 'status']
        for field in required_fields:
            if field not in order:
                issues.append(f'Missing {field}')
        
        if order.get('amount', 0) < 30:
            issues.append('Amount less than minimum (₹30)')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'order': order
        }
    except Exception as e:
        return {'valid': False, 'error': str(e)}

# ================================================
# CLEANUP (for testing/demo)
# ================================================

def delete_user(uid: str) -> bool:
    """Delete a user (dangerous - use with caution)"""
    try:
        db.collection(USERS_COLLECTION).document(uid).delete()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def delete_order(order_id: str) -> bool:
    """Delete an order (dangerous - use with caution)"""
    try:
        db.collection(ORDERS_COLLECTION).document(order_id).delete()
        return True
    except Exception as e:
        print(f"Error deleting order: {e}")
        return False

# ================================================
# TEST/DEMO FUNCTIONS
# ================================================

def create_demo_user(email: str) -> str:
    """Create a demo user and return UID"""
    try:
        uid = email.split('@')[0] + '_demo'
        create_user(uid, email)
        add_balance_to_user(uid, 500)
        return uid
    except Exception as e:
        print(f"Error creating demo user: {e}")
        return None

def create_demo_order(uid: str) -> str:
    """Create a demo order for testing"""
    try:
        order_data = {
            'uid': uid,
            'username': 'testuser',
            'service': '📸 Instagram Followers',
            'service_id': 'instagram_followers',
            'platform': 'Instagram',
            'plan': 'normal',
            'amount': 80,
            'quantity': 1000,
            'target': 'testaccount',
            'utr': 'TEST123456',
            'status': 'pending'
        }
        return save_order(order_data)
    except Exception as e:
        print(f"Error creating demo order: {e}")
        return None
