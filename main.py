"""
SMM PANEL BACKEND - PRODUCTION READY
- Firebase Firestore as DB
- Manual order handling
- Manual balance add by admin
- Render compatible (NO LOOP)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# =========================
# FIREBASE INIT (RENDER SAFE)
# =========================

if not firebase_admin._apps:
    firebase_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not firebase_json:
        raise RuntimeError("Firebase credentials missing")

    cred = credentials.Certificate(json.loads(firebase_json))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =========================
# FASTAPI INIT
# =========================

app = FastAPI(title="Infinity SMM Panel API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MODELS
# =========================

class UserCreate(BaseModel):
    uid: str
    email: str

class UsernameSet(BaseModel):
    uid: str
    username: str

class BalanceUpdate(BaseModel):
    uid: str
    amount: float
    action: str  # add | deduct | set

class OrderCreate(BaseModel):
    uid: str
    username: str
    service: str
    platform: str
    plan: str
    amount: float
    quantity: int
    target: str
    utr: str

class OrderStatus(BaseModel):
    status: str  # pending | completed | rejected

# =========================
# BASIC
# =========================

@app.get("/")
def root():
    return {"message": "SMM Panel API is running ✅"}

@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# USERS
# =========================

@app.post("/api/users/create")
def create_user(data: UserCreate):
    ref = db.collection("users").document(data.uid)
    if ref.get().exists:
        return {"success": True, "message": "User exists"}

    ref.set({
        "uid": data.uid,
        "email": data.email,
        "username": None,
        "balance": 0,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return {"success": True}

@app.get("/api/users/{uid}")
def get_user(uid: str):
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        raise HTTPException(404, "User not found")
    return doc.to_dict()

@app.post("/api/users/username")
def set_username(data: UsernameSet):
    ref = db.collection("users").document(data.uid)
    user = ref.get()
    if not user.exists:
        raise HTTPException(404, "User not found")

    if user.to_dict().get("username"):
        raise HTTPException(400, "Username already set")

    ref.update({"username": data.username})
    return {"success": True}

# =========================
# BALANCE
# =========================

@app.post("/api/users/balance")
def update_balance(data: BalanceUpdate):
    ref = db.collection("users").document(data.uid)
    user = ref.get()
    if not user.exists:
        raise HTTPException(404, "User not found")

    bal = user.to_dict().get("balance", 0)

    if data.action == "add":
        bal += data.amount
    elif data.action == "deduct":
        if bal < data.amount:
            raise HTTPException(400, "Insufficient balance")
        bal -= data.amount
    elif data.action == "set":
        bal = data.amount
    else:
        raise HTTPException(400, "Invalid action")

    ref.update({"balance": bal})
    return {"success": True, "balance": bal}

# =========================
# ORDERS
# =========================

@app.post("/api/orders")
def create_order(data: OrderCreate):
    user_ref = db.collection("users").document(data.uid)
    user = user_ref.get()

    if not user.exists:
        raise HTTPException(404, "User not found")

    balance = user.to_dict().get("balance", 0)
    if balance < data.amount:
        raise HTTPException(400, "Insufficient balance")

    # deduct balance
    user_ref.update({"balance": balance - data.amount})

    order_ref = db.collection("orders").document()
    order_ref.set({
        "order_id": order_ref.id,
        "uid": data.uid,
        "username": data.username,
        "service": data.service,
        "platform": data.platform,
        "plan": data.plan,
        "amount": data.amount,
        "quantity": data.quantity,
        "target": data.target,
        "utr": data.utr,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP
    })

    return {"success": True, "order_id": order_ref.id}

@app.get("/api/orders/user/{uid}")
def user_orders(uid: str):
    orders = db.collection("orders").where("uid", "==", uid).stream()
    return [o.to_dict() for o in orders]

@app.get("/api/orders")
def all_orders():
    orders = db.collection("orders").stream()
    return [o.to_dict() for o in orders]

@app.put("/api/orders/{order_id}")
def update_order(order_id: str, data: OrderStatus):
    ref = db.collection("orders").document(order_id)
    if not ref.get().exists:
        raise HTTPException(404, "Order not found")

    ref.update({"status": data.status})
    return {"success": True}
