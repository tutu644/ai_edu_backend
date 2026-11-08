from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import OpenAI
from database import SessionLocal, engine, Base
import models
import json
import re
from dotenv import load_dotenv

load_dotenv()
models.Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key="sk-d44280563e604ee19043b58746d3ce3f", base_url="https://api.deepseek.com/v1")
vision_client = OpenAI(api_key="4e6a4e1020fe403795041d048ec08b7f.5Hhvjwx1IqFRxa2y", base_url="https://open.bigmodel.cn/api/paas/v4/")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# 1. 文本接口
class ChatRequest(BaseModel):
    question: str
    role_style: str = "gentle"

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    json_format_rule = '请严格按照 JSON 格式返回：{"analysis": "解析", "knowledge_point": "知识点", "similar_questions": ["题1"], "mindmap": {"name": "考点", "children": [{"name": "概念", "children": [{"name": "定义"}]}]}}。严禁 Emoji！'
    system_prompt = "你是一位温柔的老师。" + json_format_rule
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": request.question}]
        )
        ai_raw_text = response.choices[0].message.content
        match = re.search(r'\{.*\}', ai_raw_text, re.DOTALL)
        if match:
            try:
                safe_json = match.group(0).replace('\\', '\\\\')
                safe_json = re.sub(r',\s*([\}\]])', r'\1', safe_json)
                ai_data = json.loads(safe_json, strict=False)
                return {"code": 200, "data": {"answer": ai_data, "mindmap": ai_data.get("mindmap")}}
            except Exception:
                pass
        return {"code": 200, "data": {"answer": {"analysis": ai_raw_text, "knowledge_point": "综合", "similar_questions": [], "mindmap": None}, "mindmap": None}}
    except Exception as e:
        return {"code": 500, "msg": str(e)}

# 2. 拍照搜题接口（究极缝合版）
class ImageChatRequest(BaseModel):
    image_base64: str 
    text: str = "" 

@app.post("/api/chat_image")
async def chat_with_image(request: ImageChatRequest, db: Session = Depends(get_db)):
    prompt = '''
你是一位特级教师。请解答图片中的题目。
必须严格遵守以下规则：
1. 绝对不准使用任何复杂的代码或 LaTeX 语法，所有公式用大白话写。
2. 必须写出详细的步骤，最后写出选哪个选项。
3. 直接输出纯文本，按照以下格式：
【解题分析】
（详细步骤）
【知识点】
【变式题】
'''
    try:
        response = vision_client.chat.completions.create(
            model="glm-4v-flash", 
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": request.image_base64}}]}]
        )
        
        ai_raw_text = response.choices[0].message.content
        
        # 清洗所有大括号等乱七八糟的符号
        clean_text = re.sub(r'\\left\[|\\right\]|\\left\(|\\right\)|\\left\\\{|\\right\\\}|\[|\]', '', ai_raw_text)
        clean_text = re.sub(r'\n+', '\n', clean_text).replace('  ', ' ')

        analysis_part = clean_text
        knowledge_part = "综合"
        similar_part = []
        
        if "【知识点】" in clean_text:
            parts1 = clean_text.split("【知识点】")
            analysis_part = parts1[0].replace("【解题分析】", "").strip()
            if "【变式题】" in parts1[1]:
                parts2 = parts1[1].split("【变式题】")
                knowledge_part = parts2[0].strip()
                similar_part = [line.strip("- ").strip() for line in parts2[1].strip().split('\n') if line.strip()]
            else:
                knowledge_part = parts1[1].strip()

        # 🚨 强行注入满血导图（4 个大分支）
        mindmap_data = {
            "name": knowledge_part if knowledge_part != "综合" else "本题核心考点",
            "children": [
                {"name": "核心概念", "children": [{"name": "基本定义"}, {"name": "关键特征"}, {"name": "相关公式"}]},
                {"name": "解题步骤", "children": [{"name": "第一步：审题"}, {"name": "第二步：推导"}, {"name": "第三步：结论"}]},
                {"name": "举一反三", "children": [{"name": "变式题型1"}, {"name": "变式题型2"}]},
                {"name": "易错防范", "children": [{"name": "常见陷阱"}, {"name": "计算细节"}]}
            ]
        }

        new_question = models.Question(original_text="[图片]", analysis=analysis_part, knowledge_point=knowledge_part)
        db.add(new_question)
        db.commit()
        
        return {
            "code": 200, 
            "data": {
                "answer": {
                    "analysis": analysis_part, 
                    "knowledge_point": knowledge_part, 
                    "similar_questions": similar_part, 
                    "mindmap": mindmap_data
                }, 
                "mindmap": mindmap_data
            }
        }
    except Exception as e:
        return {"code": 500, "msg": f"请求失败: {str(e)}"}

# 3. 错题本接口
class MistakeRequest(BaseModel):
    question: str
    analysis: str
    knowledge_point: str

@app.post("/api/mistakes")
async def add_mistake(request: MistakeRequest, db: Session = Depends(get_db)):
    new_mistake = models.Mistake(user_id=1, question=request.question, analysis=request.analysis, knowledge_point=request.knowledge_point)
    db.add(new_mistake)
    db.commit()
    return {"code": 200, "msg": "成功"}

@app.get("/api/mistakes")
async def get_mistakes(db: Session = Depends(get_db)):
    mistakes = db.query(models.Mistake).filter(models.Mistake.user_id == 1).all()
    return {"code": 200, "data": [{"id": m.id, "question": m.question, "analysis": m.analysis, "knowledge_point": m.knowledge_point} for m in mistakes]}