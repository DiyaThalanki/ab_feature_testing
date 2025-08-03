# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import jwt  
import bcrypt
import os

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT settings
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="Book Subscription API")

# CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    subscription_plan = Column(String, default="free")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user_books = relationship("UserBook", back_populates="user")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    genre = Column(String)
    description = Column(String)
    price = Column(Float)
    is_premium = Column(Boolean, default=False)
    
    user_books = relationship("UserBook", back_populates="book")

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    price = Column(Float)
    description = Column(String)
    max_books = Column(Integer)

class UserBook(Base):
    __tablename__ = "user_books"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    is_read = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="user_books")
    book = relationship("Book", back_populates="user_books")

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models for API requests/responses
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    subscription_plan: str
    is_active: bool
    
    class Config:
        from_attributes = True

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    genre: str
    description: str
    price: float
    is_premium: bool
    
    class Config:
        from_attributes = True

class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    max_books: int
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(email: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# API Endpoints

@app.get("/")
def read_root():
    return {"message": "Book Subscription API"}

# Authentication endpoints
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = hash_password(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Book endpoints
@app.get("/books", response_model=List[BookResponse])
def get_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.post("/books/{book_id}/add-to-library")
def add_book_to_library(
    book_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if user already has this book
    existing = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Book already in library")
    
    # Check if premium book and user has free plan
    if book.is_premium and current_user.subscription_plan == "free":
        raise HTTPException(status_code=403, detail="Premium subscription required")
    
    # Add book to user's library
    user_book = UserBook(user_id=current_user.id, book_id=book_id)
    db.add(user_book)
    db.commit()
    
    return {"message": "Book added to library"}

@app.get("/my-books", response_model=List[BookResponse])
def get_my_books(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_books = db.query(UserBook).filter(UserBook.user_id == current_user.id).all()
    books = [user_book.book for user_book in user_books]
    return books

@app.post("/books/{book_id}/mark-read")
def mark_book_as_read(
    book_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book_id
    ).first()
    
    if not user_book:
        raise HTTPException(status_code=404, detail="Book not in your library")
    
    user_book.is_read = True
    db.commit()
    
    return {"message": "Book marked as read"}

# Subscription endpoints
@app.get("/subscription-plans", response_model=List[SubscriptionPlanResponse])
def get_subscription_plans(db: Session = Depends(get_db)):
    plans = db.query(SubscriptionPlan).all()
    return plans

@app.post("/subscribe/{plan_id}")
def subscribe_to_plan(
    plan_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    
    current_user.subscription_plan = plan.name
    db.commit()
    
    return {"message": f"Successfully subscribed to {plan.name} plan"}

# Seed data function (call this once to populate your database)
@app.post("/seed-data")
def seed_data(db: Session = Depends(get_db)):
    # Check if data already exists
    if db.query(Book).first():
        return {"message": "Data already exists"}
    
    # Create subscription plans
    plans = [
        SubscriptionPlan(name="free", price=0.0, description="Access to basic books", max_books=5),
        SubscriptionPlan(name="premium", price=9.99, description="Access to all books", max_books=100),
        SubscriptionPlan(name="unlimited", price=19.99, description="Unlimited access", max_books=999)
    ]
    
    for plan in plans:
        db.add(plan)
    
    # Create sample books
    books = [
        Book(title="The Python Guide", author="John Doe", genre="Programming", 
             description="Learn Python programming", price=29.99, is_premium=False),
        Book(title="Advanced FastAPI", author="Jane Smith", genre="Programming", 
             description="Master FastAPI development", price=39.99, is_premium=True),
        Book(title="Data Science Handbook", author="Bob Johnson", genre="Data Science", 
             description="Complete guide to data science", price=49.99, is_premium=True),
        Book(title="Web Development Basics", author="Alice Brown", genre="Web Development", 
             description="HTML, CSS, JavaScript fundamentals", price=19.99, is_premium=False),
        Book(title="Machine Learning Primer", author="Charlie Wilson", genre="AI/ML", 
             description="Introduction to machine learning", price=34.99, is_premium=True)
    ]
    
    for book in books:
        db.add(book)
    
    db.commit()
    return {"message": "Sample data created successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)