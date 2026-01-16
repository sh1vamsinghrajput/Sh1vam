"""
SMM PANEL - BACKEND API (FastAPI)
This backend handles:
- User management verification
- Balance operations
- Order processing
- Admin operations
All data is stored in Firestore (server-side)
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
from firebase_admin_ops import (
    db,
    create_user,
    get_user,
    update_user_balance,
    add_balance_to_user,
    deduct_user_balance,
    save_order,
    get_user_orders,
    get_all_orders,
    update_order_status,
    get_all_users,
    get_order_stats,
    get_user_stats
)

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="SMM Panel API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================
# PYDANTIC MODELS
# ================================================

class UserCreate(BaseModel):
    uid: str
    email: str

class SetUsername(BaseModel):
    uid: str
    username: str

class BalanceOperation(BaseModel):
    uid: str
    amount: float
    action: str  # 'add', 'set', 'deduct'

class OrderCreate(BaseModel):
    uid: str
    username: str
    service: str
    service_id: str
    platform: str
    plan: str  # 'normal' or 'premium'
    amount: float
    quantity: int
    target: str
    utr: str

class OrderUpdate(BaseModel):
    order_id: str
    status: str  # 'pending' or 'completed'

class OrderFilter(BaseModel):
    status: Optional[str] = None  # None, 'pending', or 'completed'

# ================================================
# HEALTH CHECK
# ================================================

@app.get("/")
async def root():
    return {"message": "SMM Panel API is running ✅"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

# ================================================
# USER ENDPOINTS
# ================================================

@app.post("/api/users/create")
async def create_new_user(user_data: UserCreate):
    """Create a new user in Firestore"""
    try:
        create_user(user_data.uid, user_data.email)
        return {"success": True, "message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users/{uid}")
async def get_user_data(uid: str):
    """Get user data by UID"""
    try:
        user = get_user(uid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "data": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/users/{uid}/username")
async def set_user_username(uid: str, data: SetUsername):
    """Set username for user (one-time only)"""
    try:
        user = get_user(uid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.get('username'):
            raise HTTPException(status_code=400, detail="Username already set")
        
        update_user_balance(uid, {"username": data.username})
        return {"success": True, "message": "Username set successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users/{uid}/balance")
async def get_user_balance(uid: str):
    """Get user balance"""
    try:
        user = get_user(uid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "balance": user.get('balance', 0)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/users/{uid}/balance")
async def modify_user_balance(uid: str, data: BalanceOperation):
    """Modify user balance (add, set, deduct)"""
    try:
        user = get_user(uid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if data.action == 'add':
            result = add_balance_to_user(uid, data.amount)
        elif data.action == 'set':
            result = update_user_balance(uid, {'balance': data.amount})
        elif data.action == 'deduct':
            current_balance = user.get('balance', 0)
            if current_balance < data.amount:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            result = deduct_user_balance(uid, data.amount)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        return {"success": True, "message": f"Balance {data.action}ed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users")
async def get_all_users_list():
    """Get all users (Admin only in production)"""
    try:
        users = get_all_users()
        return {"success": True, "users": users}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ================================================
# ORDER ENDPOINTS
# ================================================

@app.post("/api/orders")
async def create_new_order(order_data: OrderCreate):
    """Create a new order"""
    try:
        # Verify user has sufficient balance
        user = get_user(order_data.uid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.get('balance', 0) < order_data.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Deduct balance
        deduct_user_balance(order_data.uid, order_data.amount)
        
        # Save order
        order_id = save_order({
            'uid': order_data.uid,
            'username': order_data.username,
            'service': order_data.service,
            'service_id': order_data.service_id,
            'platform': order_data.platform,
            'plan': order_data.plan,
            'amount': order_data.amount,
            'quantity': order_data.quantity,
            'target': order_data.target,
            'utr': order_data.utr,
            'status': 'pending'
        })
        
        return {"success": True, "order_id": order_id, "message": "Order created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/orders/user/{uid}")
async def get_user_orders_list(uid: str):
    """Get all orders for a user"""
    try:
        orders = get_user_orders(uid)
        return {"success": True, "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/orders")
async def get_all_orders_list(status: Optional[str] = None):
    """Get all orders (optionally filtered by status)"""
    try:
        orders = get_all_orders()
        if status:
            orders = [o for o in orders if o.get('status') == status]
        return {"success": True, "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/orders/{order_id}")
async def update_order_status_endpoint(order_id: str, data: OrderUpdate):
    """Update order status (Admin only)"""
    try:
        update_order_status(order_id, data.status)
        return {"success": True, "message": f"Order status updated to {data.status}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ================================================
# ANALYTICS ENDPOINTS
# ================================================

@app.get("/api/stats/orders")
async def get_order_stats_endpoint():
    """Get order statistics"""
    try:
        stats = get_order_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stats/users")
async def get_user_stats_endpoint():
    """Get user statistics"""
    try:
        stats = get_user_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stats")
async def get_all_stats():
    """Get all statistics"""
    try:
        order_stats = get_order_stats()
        user_stats = get_user_stats()
        return {
            "success": True,
            "orders": order_stats,
            "users": user_stats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ================================================
# ERROR HANDLERS
# ================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return {
        "success": False,
        "error": str(exc)
    }

# ================================================
# RUN SERVER
# ================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run with: python main.py
    # Or: uvicorn main:app --reload
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
