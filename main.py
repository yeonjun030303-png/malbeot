import os
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from google import genai
from google.genai import types

# 1. DB 설정 (SQLite)
DATABASE_URL = "sqlite:///./rice_app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DB 모델 정의
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    rice_points = Column(Integer, default=0)

class PointLog(Base):
    __tablename__ = "point_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# 3. FastAPI 및 Gemini SDK 초기화
app = FastAPI(
    title="Rice (쌀) - 한옥 감성 커뮤니티 API",
    description="한옥의 따뜻함을 담은 커뮤니티 백엔드 API 서버입니다. 🌾",
    version="1.0.0"
)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request Schemas
class UserCreate(BaseModel):
    username: str

class ChatRequest(BaseModel):
    username: str
    prompt: str = "한옥의 따뜻한 감성으로 인사를 건네주세요."

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {
        "message": "따뜻한 한옥 감성 커뮤니티 '쌀(Rice)' 서버가 가동 중입니다. 🌾",
        "status": "online"
    }

@app.post("/api/users", summary="유저 생성 및 초기 쌀 포인트 지급")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        return {"message": "이미 존재하는 유저입니다.", "user": existing_user}
    
    new_user = User(username=user_data.username, rice_points=10) # 가입 축하 10알
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "유저가 생성되었습니다! (쌀 10알 지급)", "user": new_user}

@app.get("/api/users/{username}", summary="유저 정보 및 쌀 포인트 조회")
def get_user_info(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    return user

@app.post("/api/ai-chat", summary="한옥 AI 대화 & 쌀 포인트 적립")
def ai_chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not client:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY가 설정되지 않았습니다. 환경변수를 확인해 주세요."
        )

    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다. /api/users 에서 먼저 생성해주세요.")

    system_instruction = (
        "너는 따뜻하고 고즈넉한 한옥 커뮤니티 '쌀(Rice)'의 안내원이야. "
        "정감 있고 따뜻한 한국어 문체로 친절하게 응답해 줘."
    )

    ai_reply = ""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=req.prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            ai_reply = response.text
            break
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                ai_reply = "지금은 한옥 툇마루에 손님이 너무 많이 몰렸네요. 🍵 잠시 차 한 잔 드시고 다시 말씀해 주세요."
            else:
                ai_reply = f"AI 통신 중 오류가 발생했습니다: {error_msg}"

    # 쌀 포인트 적립 (+5알)
    user.rice_points += 5
    log = PointLog(user_id=user.id, amount=5, reason="AI 대화 출석 적립")
    db.add(log)
    db.commit()

    return {
        "username": user.username,
        "ai_response": ai_reply,
        "earned_rice": 5,
        "total_rice_points": user.rice_points
    }