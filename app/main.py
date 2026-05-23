from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, File, UploadFile, Form, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import httpx
import os
import shutil
import logging
import asyncio
import json
import re
import math
import time
import concurrent.futures
import threading
from datetime import timedelta
import json_repair
from langchain_community.document_loaders import PyPDFLoader

# Suppress pypdf warnings about page labels
logging.getLogger("pypdf").setLevel(logging.ERROR)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# Global embeddings model using OpenRouter
embeddings_model = OpenAIEmbeddings(
    model="google/gemini-embedding-2-preview",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY", "dummy"),
    check_embedding_ctx_length=False,
    model_kwargs={"encoding_format": "float"}
)
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from typing import Annotated, TypedDict, List
import operator

from . import models, schemas, auth, stop_router
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gemminate")
app.include_router(stop_router.router)

# Ensure upload directory exists
UPLOAD_DIR = "static/uploads"
VECTOR_DIR = "static/vector_stores"
for d in [UPLOAD_DIR, VECTOR_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# LangGraph Setup
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], operator.add]
    context: str

async def call_model(state: AgentState, config: RunnableConfig):
    system_prompt = (
        "You are an expert textbook reading assistant. "
        "Your goal is to answer the user's question clearly and accurately based on the provided textbook context snippets. "
        "Structure your response beautifully using Markdown (e.g., headings, bullet points, bold text) to make it highly readable, similar to Claude's outputs. "
        "IMPORTANT: Whenever you use mathematical formulas, ALWAYS use LaTeX notation with standard delimiters: "
        "Use \\\\( ... \\\\) for inline formulas and \\\\[ ... \\\\] for block formulas. "
        "Do not use plain brackets [ ] or parentheses ( ) for math without the preceding backslashes. "
        "CRITICAL: If you are outputting JSON, you MUST double-escape all backslashes in your LaTeX formulas so the JSON remains valid (e.g., use \\\\alpha instead of \\alpha, and \\\\frac instead of \\frac)."
        "\n\nIMPORTANT CITE INSTRUCTIONS: "
        "Do not write out large quotes in the body of your text. Instead, write your explanation in your own words. "
        "Whenever you use information from a snippet, you MUST include an inline citation using this exact format: "
        "<ref quote=\"exact short quote\">SnippetNumber</ref>. "
        "The 'quote' attribute MUST be the exact short text (a few words to a sentence) from the context snippet that supports your point. "
        "Example: ...this is a proven fact <ref quote=\"studies show this fact is proven\">3</ref>.\n"
        "If the context does not contain the answer, use your general knowledge to provide a complete and accurate answer without apologizing."
        "\n\nQUIZ/FLASHCARD/VISUAL GENERATION RULES:"
        "\nIf the user explicitly asks for a visual (e.g. '@visual', 'Generate a visual'), you MUST output a FULL AND COMPLETE HTML DOCUMENT starting with <!DOCTYPE html> and ending with </html>. WRAP the HTML inside a standard markdown code block (```html ... ```). The visual should re-explain the concept pedagogically. "
        "The HTML code can include inline CSS, JavaScript, D3.js, or Three.js for 3D visualizations. While D3.js is preferred for most data-driven diagrams, use Three.js when a 3D perspective would significantly enhance the explanation. Make the visual highly interactive, engaging, and detailed. Ensure it provides an intuitive explanation of the concept, utilizing animations, tooltips, and interactive controls to demonstrate the principles effectively. "
        "The first line of the HTML MUST contain a comment with the term name like this: <!-- TERM: Concept Name -->"
        "\n\nWhen generating D3.js or Three.js visuals, you MUST follow these specific principles and aesthetic guidelines:\n"
        "- Declarative Selection: Use d3.select() and d3.selectAll() to bind data to DOM elements.\n"
        "- Scales & Axes: Leverage d3.scaleLinear(), d3.scaleTime(), etc., to map data domains to visual ranges. Make axes clear and well-labeled.\n"
        "- Transitions: Use .transition() for smooth animations of data changes. Add meaningful animations to demonstrate the concept in action.\n"
        "- Interactivity: Add tooltips on hover, click events, and interactive sliders or buttons to let the user manipulate variables and observe changes.\n"
        "- Responsiveness: Always use viewBox on SVG elements and update dimensions using getBoundingClientRect() on window resize.\n"
        "- Boundary Constraints (CRITICAL): Whenever D3 is used to display, animate, or drag objects within a canvas/SVG (especially with d3.forceSimulation), you MUST strictly constrain their coordinates to prevent them from straying off-screen or becoming invisible. Enforce bounding boxes inside the tick function or drag handlers (e.g., d.x = Math.max(padding, Math.min(width - padding, d.x)); d.y = Math.max(padding, Math.min(height - padding, d.y));). Never let objects get pushed out of sight by repulsion forces.\n"
        "- Aesthetic Guidelines: Modular Spatial Intelligence. Treat the header, visualization area, readout cards, and control panel as distinct modules. Use the primary palette: Blue (#378ADD), Green (#1D9E75), Orange (#D85A30), Purple (#7F77DD), Gray (#888780), with vibrant gradients where appropriate.\n"
        "- Layout: Use a root flex container (display: flex; flex-direction: column; height: 100vh;). The Main Hero SVG should occupy flex: 1; min-height: 0; position: relative;. Readout Cards should use background #f0eeea, border-radius 8px, and monospace values. Formula Chips use background #ebebeb, border-radius 7px, and monospace font. Place sliders and buttons in a bottom panel with a subtle border (1px solid #e5e7eb). Use accent-color: #7F77DD for sliders. Add clear instructions on how to interact with the visual.\n"
        "ALWAYS GENERATE HTML code EXACTLY like this template, providing a complete, working D3 implementation inside the render function. The input image text is for guidance ONLY:\n"
        "```html\n<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Magnetic Force on a Moving Charge</title>\n    <script src=\"https://d3js.org/d3.v7.min.js\"></script>\n    <style>\n        :root {\n            --primary: #378ADD;   /* Blue for B-field */\n            --secondary: #1D9E75; /* Green for Velocity */\n            --accent: #D85A30;    /* Orange for Force */\n            --charge-color: #7F77DD; /* Purple for Charge */\n            --bg: #f0eeea;\n            --card-bg: #ffffff;\n            --text: #333;\n        }\n\n        body {\n            margin: 0;\n            padding: 0;\n            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;\n            background-color: var(--bg);\n            color: var(--text);\n            display: flex;\n            flex-direction: column;\n            height: 100vh;\n            overflow: hidden;\n        }\n\n        #cleeroute-module {\n            display: flex;\n            flex-direction: column;\n            height: 100%;\n        }\n\n        .header {\n            padding: 15px 25px;\n            background: white;\n            display: flex;\n            justify-content: space-between;\n            align-items: center;\n            box-shadow: 0 2px 5px rgba(0,0,0,0.1);\n            z-index: 10;\n        }\n\n        .header h1 {\n            margin: 0;\n            font-size: 1.4rem;\n            color: var(--text);\n        }\n\n        .formula-chip {\n            background: #ebebeb;\n            padding: 5px 12px;\n            border-radius: 7px;\n            font-family: 'Courier New', Courier, monospace;\n            font-weight: bold;\n            font-size: 0.9rem;\n        }\n\n        .visual-container {\n            flex: 1;\n            position: relative;\n            min-height: 0;\n            background: #ffffff;\n        }\n\n        svg {\n            width: 100%;\n            height: 100%;\n            display: block;\n        }\n\n        .readout {\n            display: grid;\n            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));\n            gap: 15px;\n            padding: 20px;\n            background: var(--bg);\n        }\n\n        .card {\n            background: var(--card-bg);\n            padding: 15px;\n            border-radius: 8px;\n            box-shadow: 0 2px 4px rgba(0,0,0,0.05);\n            text-align: center;\n        }\n\n        .card-label {\n            font-size: 0.8rem;\n            text-transform: uppercase;\n            color: #888780;\n            margin-bottom: 5px;\n        }\n\n        .card-val {\n            font-family: 'Courier New', Courier, monospace;\n            font-size: 1.1rem;\n            font-weight: bold;\n            color: var(--primary);\n        }\n\n        .controls {\n            padding: 15px 25px;\n            background: white;\n            border-top: 1px solid #e5e7eb;\n            display: flex;\n            align-items: center;\n            gap: 20px;\n        }\n\n        input[type=range] {\n            flex: 1;\n            accent-color: var(--accent);\n        }\n\n        label {\n            font-weight: bold;\n            font-size: 0.9rem;\n        }\n\n        /* Vector styling */\n        .vector-arrow {\n            stroke-linecap: round;\n            stroke-linejoin: round;\n        }\n    </style>\n</head>\n<body>\n\n<div id=\"cleeroute-module\">\n    <div class=\"header\">\n        <h1>Concept Title Here</h1>\n        <div class=\"formula-chip\">Formula Here</div>\n    </div>\n\n    <div class=\"visual-container\" id=\"container\">\n        <svg id=\"viz\"></svg>\n    </div>\n\n    <div class=\"readout\">\n        <div class=\"card\">\n            <div class=\"card-label\">Variable 1</div>\n            <div class=\"card-val\" id=\"var1-display\">0.00</div>\n        </div>\n    </div>\n\n    <div class=\"controls\">\n        <label>Control 1</label>\n        <input type=\"range\" id=\"var1-slider\" min=\"0\" max=\"100\" value=\"50\">\n    </div>\n</div>\n\n<script>\n    const svg = d3.select(\"#viz\");\n    const container = document.getElementById('container');\n    \n    let width, height, centerX, centerY;\n\n    function updateDimensions() {\n        const rect = container.getBoundingClientRect();\n        width = rect.width;\n        height = rect.height;\n        centerX = width / 2;\n        centerY = height / 2;\n        svg.attr(\"viewBox\", `0 0 ${width} ${height}`);\n        render();\n    }\n\n    function render() {\n        svg.selectAll(\"*\").remove();\n        // D3 implementation here...\n    }\n\n    window.addEventListener('resize', updateDimensions);\n    updateDimensions();\n</script>\n</body>\n</html>\n```\n"
        "\nIf the user explicitly asks for a quiz (e.g. '@quiz', 'Generate a quiz'), you MUST output ONLY a valid JSON object. "
        "Do not include any conversational text before or after the JSON. "
        "Structure the quiz JSON exactly like this:"
        "\n{\n  \"title\": \"Quiz Title\",\n  \"questions\": [\n    {\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct_index\": 0, \"explanation\": \"Explanation for the correct answer\"}\n  ]\n}"
        "\nIf the user explicitly asks for flashcards (e.g. '@flashcard', 'Generate flashcards'), you MUST output ONLY a valid JSON object. "
        "Do not include any conversational text before or after the JSON. "
        "Structure the flashcard set JSON exactly like this:"
        "\n{\n  \"title\": \"Flashcards Title\",\n  \"cards\": [\n    {\"front\": \"...\", \"back\": \"...\"}\n  ]\n}"
        "\nIMPORTANT: If the user asks for a specific number of items (e.g., '3 quizzes' or '5 flashcards'), this means they want ONE set containing exactly that many questions or cards. "
        "Generate exactly the number of questions or cards requested within the single JSON object."
        "\n\nSUMMARY REQUESTS:"
        "\nIf the user requests a summary (e.g., '@summary'), they may specify a type like 'detailed', 'brief', 'bullet-point', 'faq', or 'glossary'. "
        "Provide the summary in the requested style based on the textbook context snippets. "
        "These are standard conversational responses, not JSON."
        "\n\nContext Snippets:\n" + state['context']
    )
    messages = [SystemMessage(content=system_prompt)] + state['messages']

    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=4096,
        streaming=True
    )

    full_response = ""
    async for chunk in llm.astream(messages, config=config):
        full_response += chunk.content
        
    return {"messages": [AIMessage(content=full_response)]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)
rag_agent = workflow.compile()

# RAG Helpers
def update_goal_status(goal_id: int, status: str, message: str, db_session_factory, log_entry: dict = None):
    db = db_session_factory()
    try:
        goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
        if goal:
            if goal.status == "completed" and status == "processing":
                # Do not revert to processing if we are already in the completed (classroom) state
                pass
            else:
                goal.status = status
            goal.status_message = message
            if log_entry:
                logs = []
                if goal.processing_logs:
                    try:
                        logs = json.loads(goal.processing_logs)
                    except:
                        pass
                logs.append(log_entry)
                goal.processing_logs = json.dumps(logs)
            db.commit()
    finally:
        db.close()


_toc_lock = threading.Lock()

def process_page_range(pdf_path, start_page, end_page):
    """
    Worker function that opens the PDF once and processes a range of pages.
    """
    import fitz
    import re
    
    doc = fitz.open(pdf_path)
    headings = []
    
    # Common patterns to filter out or identify
    noise_patterns = [
        r'^\d+$', # Just numbers (page numbers)
        r'^Figure\s+\d+', 
        r'^Table\s+\d+',
        r'^Page\s+\d+',
        r'^\d+\s+of\s+\d+$'
    ]
    
    for page_num in range(start_page, end_page):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        # Heuristic: Headings are usually larger and/or bold
                        is_likely_heading = s["size"] > 12 or (s["size"] > 10.5 and "Bold" in s["font"])
                        if is_likely_heading:
                            clean_text = s["text"].strip()
                            # Filter out noise
                            if clean_text and len(clean_text) > 3:
                                if not any(re.search(p, clean_text, re.I) for p in noise_patterns):
                                    headings.append({
                                        "text": clean_text,
                                        "size": round(s["size"], 1),
                                        "bold": "Bold" in s["font"],
                                        "page": page_num + 1
                                    })
    doc.close()
    return headings

def extract_toc_parallel(pdf_path, max_pages=60):
    import fitz
    with _toc_lock:
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), max_pages)
        doc.close()
    
    num_cores = os.cpu_count() or 2
    pages_per_core = math.ceil(total_pages / num_cores)
    
    segments = []
    for i in range(num_cores):
        start = i * pages_per_core
        end = min(start + pages_per_core, total_pages)
        if start < end:
            segments.append((start, end))
            
    all_headings = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = [
            executor.submit(process_page_range, pdf_path, start, end) 
            for start, end in segments
        ]
        for future in concurrent.futures.as_completed(futures):
            all_headings.extend(future.result())
            
    return sorted(all_headings, key=lambda x: x['page'])

def headings_to_tree_json(headings, goal_title="", goal_description=""):
    if not headings:
        return []
        
    # Filter unique headings to avoid duplicates
    seen_headings = set()
    unique_headings = []
    for h in headings:
        key = (h['text'].lower(), h['page'])
        if key not in seen_headings:
            unique_headings.append(h)
            seen_headings.add(key)
    
    headings = unique_headings
    sizes = sorted(list(set([h['size'] for h in headings])), reverse=True)
    
    chapters = []
    last_nodes = { -1: "root" }
    
    # Heuristic for top-level chapters: largest font sizes
    top_level_sizes = sizes[:2] if len(sizes) > 1 else sizes
    
    for i, h in enumerate(headings):
        node_id = f"node_{i}"
        level = sizes.index(h['size'])
        
        # Determine if this should be a top-level chapter
        # 1. Largest font size
        # 2. Contains keywords like "Chapter", "Section", "Part"
        # 3. If it's the first heading
        is_top_level = h['size'] in top_level_sizes or re.match(r'^(Chapter|Section|Part|Unit|Module)\s+\d+', h['text'], re.I)
        
        if is_top_level:
            chapters.append({
                "id": i,
                "title": h['text'],
                "start": h['page'],
                "selected": False, 
                "children": []
            })
            last_nodes[level] = node_id
            
        last_nodes[level] = node_id
        for l in list(last_nodes.keys()):
            if l > level:
                del last_nodes[l]
    
    # Provide a flat list of top-level chapters for extract_toc_task to show to the user
    for i in range(len(chapters)):
        if i < len(chapters) - 1:
            chapters[i]["end"] = chapters[i+1]["start"] - 1
        else:
            chapters[i]["end"] = chapters[i]["start"] + 50

    # Apply selection logic:
    # 1. Identify "target" chapters based on goal keywords
    target_indices = []
    keywords = (goal_title + " " + (goal_description or "")).lower().split()
    # Filter keywords to keep only meaningful ones
    meaningful_keywords = [kw for kw in keywords if len(kw) > 3 and kw not in ['master', 'learn', 'understand', 'study', 'basics', 'intro', 'introduction']]
    
    for idx, ch in enumerate(chapters):
        ch_title_lower = ch['title'].lower()
        if any(kw in ch_title_lower for kw in meaningful_keywords):
            target_indices.append(idx)
            ch['selected'] = True
    
    # 2. If no target found, select first few by default
    if not target_indices:
        for ch in chapters[:3]: 
            ch['selected'] = True
        target_indices = [idx for idx in range(min(len(chapters), 3))]

    # 3. CRITICAL: Select all chapters BEFORE the last preselected one
    if target_indices:
        last_preselected_idx = max(target_indices)
        for idx in range(last_preselected_idx):
            chapters[idx]['selected'] = True

    return chapters

def extract_toc_task(goal_id: int, pdf_path: str, title: str, description: str, db_session_factory):
    import fitz
    try:
        update_goal_status(goal_id, "processing", "Extracting TOC from PDF...", db_session_factory)
        
        doc = fitz.open(pdf_path)
        
        # Skip built-in bookmarks as requested
        first_pages_text = ""
        
        # Extract text from first 25 pages for TOC
        update_goal_status(goal_id, "processing", "Scanning first 25 pages for TOC text...", db_session_factory)
        num_pages_to_scan = min(25, doc.page_count)
        toc_pages_text = ""
        for i in range(num_pages_to_scan):
            page_text = doc[i].get_text()
            # TOC keyword matching
            keywords = ["contents", "index", "chapter", "preface", "foreword"]
            if any(kw in page_text.lower() for kw in keywords):
                toc_pages_text += f"\n--- PDF Page Index: {i+1} ---\n"
                toc_pages_text += page_text
        
        if not toc_pages_text:
            # Fallback to first 25 pages if no keywords found
            for i in range(min(25, doc.page_count)):
                toc_pages_text += f"\n--- PDF Page Index: {i+1} ---\n"
                toc_pages_text += doc[i].get_text()

        first_pages_text = (first_pages_text + "\n" + toc_pages_text).strip()

        update_goal_status(goal_id, "processing", "AI analyzing TOC and selecting relevant chapters...", db_session_factory)
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        llm = ChatOpenAI(
            model="google/gemma-4-26b-a4b-it",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=4000,
            default_headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://gemminate.com", # Required for some OpenRouter models
                "X-Title": "Gemminate"
            }
        )

        prompt = (
            f"Given a learning goal with Title: '{title}' and Description: '{description}'.\n"
            f"Here is the text from the first pages of a textbook, which likely includes the Table of Contents. "
            f"The absolute PDF page indices are clearly marked with '--- PDF Page Index: N ---'.\n\n"
            f"{first_pages_text}\n\n"
            "Your task is to precisely locate ALL main chapters in this textbook and calculate their EXACT START and END PDF page indices.\n\n"
            "CRITICAL RULES FOR PAGE NUMBERING:\n"
            "1. PDFs have an 'Offset'. The PRINTED page number you see in the Table of Contents text is almost NEVER the same as the absolute PDF Page Index.\n"
            "2. For example, if the TOC says Chapter 1 is on printed Page 1, but the PDF itself has 14 pages of covers, title pages, and roman numeral prefaces before Chapter 1, then the PDF Page Index for Chapter 1 is 15. The offset is +14.\n"
            "3. TO FIND THE OFFSET: Look at the actual '--- PDF Page Index: N ---' markers in the text I provided. Find where Chapter 1 (or the first major chapter) actually begins in the provided text. What is the '--- PDF Page Index: N ---' for that text? Calculate: (PDF Page Index) - (Printed Page Number in TOC) = Offset.\n"
            "4. Apply this exact Offset to EVERY chapter listed in the TOC to find its true PDF start page.\n"
            "5. The end page of a chapter is exactly 1 page before the start page of the NEXT chapter.\n\n"
            "IMPORTANT: Always enumerate ALL chapters found in the TOC. Do not group the entire document into a single chapter if multiple chapters are listed. I want a detailed list of all chapters.\n\n"
            "First, output a `<thinking>` block where you:\n"
            "- Identify the printed page number for Chapter 1 from the TOC.\n"
            "- Identify the exact PDF Page Index where Chapter 1's text actually begins in the provided document snippet.\n"
            "- Calculate the Offset.\n"
            "- List 3 other chapters and verify the Offset works for them.\n\n"
            "Then, output the final result inside a ```json block as a JSON array of objects. Each object MUST have:\n"
            "- \"id\": integer starting from 0\n"
            "- \"title\": the title of the chapter\n"
            "- \"start\": the calculated PDF Page Index (integer)\n"
            "- \"end\": the calculated PDF Page Index (integer)\n"
            "- \"selected\": boolean (true if relevant to the user's goal, false otherwise)"
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        chapters = []
        
        try:
            import re
            json_match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if json_match:
                chapters = json_repair.loads(json_match.group(0))
            else:
                chapters = json_repair.loads(response.content)
            if not isinstance(chapters, list):
                chapters = []
                
            # Filter out any non-dict items that might have been returned by json_repair
            valid_chapters = []
            for c in chapters:
                if isinstance(c, dict) and "title" in c:
                    valid_chapters.append(c)
            chapters = valid_chapters
            
        except:
            chapters = []

        if not chapters:
            # If no TOC found by LLM, just pre-select the whole book as 1 chapter
            chapters.append({"id": 0, "title": "Full Document", "start": 1, "end": doc.page_count, "selected": True})

        # --- THIS IS WHERE WE APPLY THE "SELECT CHAPTERS BEFORE PRESELECTED ONES" LOGIC ---
        target_indices = [i for i, ch in enumerate(chapters) if ch.get('selected', False)]
        if target_indices:
            last_preselected_idx = max(target_indices)
            for i in range(last_preselected_idx):
                chapters[i]['selected'] = True

        chapters_json = json.dumps(chapters)
        db = db_session_factory()
        try:
            goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
            if goal:
                goal.chapters_data = chapters_json
                goal.status = "waiting_for_chapters"
                goal.status_message = "Please confirm the selected chapters."
                db.commit()
        finally:
            db.close()

    except Exception as e:
        update_goal_status(goal_id, "failed", f"Error in TOC extraction: {str(e)}", db_session_factory)

async def get_subchapters_for_chapter(chapter, doc, api_key, goal_id, db_session_factory):
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        llm = ChatOpenAI(
            model="google/gemma-4-26b-a4b-it",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=2000
        )
        
        # --- HEADER SEEKING LOGIC ---
        # Strictly respect the chapter boundaries provided in TOC
        start_val = chapter.get('start', 1)
        end_val = chapter.get('end', doc.page_count)
        
        # Limit text extraction to the actual chapter pages to avoid mixups
        # Limit to first 25 pages of the chapter for better coverage of all subchapters
        start_page_idx = max(0, start_val - 1)
        end_page_idx = min(doc.page_count, end_val)
        num_pages = min(25, max(1, end_page_idx - start_page_idx))
        
        chapter_text = ""
        for i in range(start_page_idx, start_page_idx + num_pages):
            chapter_text += f"\n--- PDF Page Index: {i+1} ---\n"
            chapter_text += doc[i].get_text()

        update_goal_status(goal_id, "processing", f"Analyzing structure of {chapter['title']} (Pages {start_page_idx+1}-{start_page_idx+num_pages})...", db_session_factory)

        prompt = (
            f"Chapter Title: {chapter['title']}\n"
            f"Here is the text from the beginning of this chapter (PDF Page Indices {start_page_idx+1} to {start_page_idx+num_pages}):\n"
            f"{chapter_text}\n\n"
            "Your task is to identify the main subchapters and key topics in this chapter. "
            "CRITICAL: For every subchapter, identify the exact PDF Page Index where it starts and where it ends. "
            "Also, for every topic, identify the exact PDF Page Index where it is discussed. "
            "The page numbers MUST correspond to the '--- PDF Page Index: N ---' markers in the text. "
            "IMPORTANT: Merge sections and topics into a single list of topics per subchapter. Topics and sections are considered the same. "
            "Return ONLY a JSON object with the following structure:\n"
            "{\n"
            "  \"subchapters\": [\n"
            "    {\n"
            "      \"title\": \"Subchapter Title (e.g. 18.1 Electric Charge)\",\n"
            "      \"start_page\": integer_page_index,\n"
            "      \"end_page\": integer_page_index,\n"
            "      \"topics\": [\n"
            "        {\"name\": \"Specific Topic 1\", \"page\": integer_page_index},\n"
            "        {\"name\": \"Specific Topic 2\", \"page\": integer_page_index}\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Do not output any markdown formatting around the JSON."
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            data = json_repair.loads(json_match.group(0))
        else:
            data = json_repair.loads(response.content)
        
        subs = data.get('subchapters', []) if isinstance(data, dict) else []
        if not isinstance(subs, list):
            subs = []
        chapter['subchapters'] = subs
    except Exception as e:
        print(f"Error extracting subchapters for {chapter['title']}: {e}")
        chapter['subchapters'] = []
    
    # Update chapters_data in DB to include subchapters as they are found
    db = db_session_factory()
    try:
        goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
        if goal:
            chapters = json.loads(goal.chapters_data)
            for c in chapters:
                if str(c['id']) == str(chapter['id']):
                    c['subchapters'] = chapter['subchapters']
                    break
            goal.chapters_data = json.dumps(chapters)
            db.commit()
    finally:
        db.close()
        
    return chapter

async def describe_topics_with_vision(goal_id, chapter, doc, api_key, db_session_factory):
    try:
        import base64
        import fitz
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        
        # We use a vision model to describe the topics in the chapter
        
        start_page = max(0, chapter['start'] - 1)
        end_page = min(doc.page_count, chapter['end'])
        
        # For each subchapter/topic, find the most relevant page and describe it
        all_topics = []
        subs = chapter.get('subchapters', [])
        if not isinstance(subs, list):
            subs = []
        for sub in subs:
            # The prompt now asks to merge sections and topics, but the structure remains the same
            for topic_obj in sub.get('topics', []):
                # Ensure topic is a string
                if isinstance(topic_obj, dict):
                    topic_name = topic_obj.get('name', 'Unknown Topic')
                    topic_page = topic_obj.get('page', start_page + 1)
                else:
                    topic_name = str(topic_obj)
                    topic_page = start_page + 1
                all_topics.append({'name': topic_name, 'page': topic_page})
        
        if not all_topics:
            return

        total_topics = len(all_topics)
        for idx, topic in enumerate(all_topics):
            topic_name = topic['name']
            topic_page = topic['page']
            
            # Use the page index from the topic itself if possible, otherwise search
            try:
                target_page_idx = max(0, int(topic_page) - 1)
            except:
                target_page_idx = start_page
            
            # Safety check: if the page doesn't contain the topic name, do a quick search in the chapter
            try:
                # Limit search range to current chapter
                page_text = doc[target_page_idx].get_text().lower()
                if topic_name.lower() not in page_text:
                    for i in range(start_page, end_page):
                        if topic_name.lower() in doc[i].get_text().lower():
                            target_page_idx = i
                            break
            except:
                pass
            
            update_goal_status(goal_id, "processing", f"Extracting visual details for {chapter['title']} - Topic {idx+1}/{total_topics}: {topic_name} (Page {target_page_idx+1})", db_session_factory)
            
            # Convert page to image
            try:
                page = doc[target_page_idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Higher resolution
                img_data = pix.tobytes("png")
                base64_image = base64.b64encode(img_data).decode('utf-8')
                
                vision_llm = ChatOpenAI(
                    model="google/gemma-4-26b-a4b-it", # using the requested model
                    openai_api_key=api_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                    max_tokens=1000
                )
                
                # Using raw OpenRouter call via httpx or just HumanMessage with image if langchain supports it here
                # Langchain HumanMessage supports content as list for vision
                msg = HumanMessage(content=[
                    {"type": "text", "text": f"""You are looking at a page from a textbook containing the topic: '{topic_name}'. 
Your goal is to provide a meta-description of what educational components are present on this page related to this topic. 

DO NOT just repeat or summarize the textbook content. Instead, describe the pedagogical layout. 
Identify and list the presence of elements such as:
- Formal Definitions
- Theoretical Explanations
- Illustrative Examples
- Worked Examples (step-by-step solutions)
- Diagrams or Illustrations (describe what they show, e.g., "A circuit diagram showing...")
- Tables or Charts
- Mathematical Formulas or Equations
- Key Highlights, Notes, or Warnings
- Practical Applications
- Review Questions or Exercises

Format your response in beautiful Markdown. Be specific about the visual structure of the page for this topic."""},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ])
                
                res = await vision_llm.ainvoke([msg])
                description_text = res.content
                
                # Save to DB
                db = db_session_factory()
                try:
                    desc = models.TopicDescription(
                        goal_id=goal_id,
                        topic_name=topic_name,
                        description=description_text
                    )
                    db.add(desc)
                    db.commit()
                finally:
                    db.close()
            except Exception as inner_e:
                print(f"Error processing topic {topic_name}: {inner_e}")
                continue
                
    except Exception as e:
        print(f"Error in vision extraction for {chapter['title']}: {e}")


async def process_single_chapter(goal_id, chapter, pdf_path, vector_store_path, api_key, db_session_factory):
    import fitz
    doc = fitz.open(pdf_path)
    try:
        start_page = chapter.get('start', 1)
        end_page = chapter.get('end', doc.page_count)
        
        # 1. Page-by-Page Analysis
        page_summaries = []
        total_pages = end_page - start_page + 1
        
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        llm = ChatOpenAI(
            model="google/gemma-4-26b-a4b-it",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=1000
        )
        
        async def analyze_page(idx):
            current_page_num = idx + 1
            page_text = doc[idx].get_text()
            
            if not page_text.strip():
                return {"page_number": current_page_num, "analysis": "Empty page."}

            prompt = (
                f"Analyze the following text from PDF Page Index {current_page_num} of the chapter '{chapter['title']}'. "
                "Describe what this page contains (definitions, key concepts, examples, diagrams, etc.). "
                "CRITICAL: Always identify and include information about any headings, titles, subheadings, or subtitles found on this page. "
                "Provide a concise summary (max 120 words).\n\n"
                f"Content:\n{page_text}"
            )
            
            try:
                # Use a specific rate limit or just let asyncio handle concurrency
                res = await llm.ainvoke([HumanMessage(content=prompt)])
                summary_data = {
                    "page_number": current_page_num,
                    "analysis": res.content
                }
                # Log progress for one of the concurrent tasks occasionally
                if current_page_num % 5 == 0:
                    rel_page = current_page_num - start_page + 1
                    update_goal_status(goal_id, "processing", f"Analyzing chapter '{chapter['title']}': Page {rel_page}/{total_pages}...", db_session_factory, log_entry={"chapter": chapter['title'], **summary_data})
                return summary_data
            except Exception as e:
                print(f"Error analyzing page {current_page_num}: {e}")
                return {"page_number": current_page_num, "analysis": "Analysis failed for this page."}

        # Concurrently analyze all pages in the chapter
        tasks = [analyze_page(i) for i in range(start_page - 1, end_page)]
        page_summaries = await asyncio.gather(*tasks)
        page_summaries.sort(key=lambda x: x['page_number'])

        # 2. Parallel Tree Synthesis and Vector Extraction
        update_goal_status(goal_id, "processing", f"Synthesizing map and indexing text for '{chapter['title']}' concurrently...", db_session_factory)
        context = "\n".join([f"Page {s['page_number']}: {s['analysis']}" for s in page_summaries])
        
        tree_prompt = (
            f"Based on the following page-by-page analyses of chapter '{chapter['title']}', create a hierarchical tree of subchapters and specific topics. "
            "CRITICAL: The tree MUST be built strictly using the actual headings, titles, subheadings, and subtitles found in the analyses. Do not invent topics; use the exact wording of the headings identified in the text. "
            "For each subchapter or topic, include the exact page number in the title (e.g. '18.1 Electric Charge (Page 360)'). "
            "Also, include an array of ALL page numbers that this part touches in a 'pages' key. "
            "CRITICAL: You MUST process ALL pages listed in the analyses. Do not skip or stop early. The chapter contains many pages, ensure every page number mentioned in the analyses is mapped to at least one node in the tree.\n"
            "ADDITIONALLY, you must intelligently and creatively inject interactive 'sections' into this tree alongside the standard topics. These sections are special nodes representing learning activities. "
            "The section types are: 'pre-requisites', 'chapter summary', 'video', 'feynmann technique', 'what-if analysis', 'quiz', 'flashcard', 'qualify'. "
            "Rules for inserting sections:\n"
            "1. CRITICAL: The very first element in the 'tree' array MUST be a node representing the chapter title itself. Inside this chapter node's 'children' array, start with 'pre-requisites' and 'chapter summary' in that order.\n"
            "2. CRITICAL: When designing the treemap, the sections MUST always be at the same hierarchical level as at least one regular treemap part (i.e., normal topics and headings). Never place sections in an isolated level without regular topics alongside them as siblings.\n"
            "3. CRITICAL - INTELLIGENT PLACEMENT: Do NOT clump all sections together at the end. You must intersperse and place 'video', 'feynmann technique', 'what-if analysis', 'quiz', and 'flashcard' sections intelligently BETWEEN normal topics, placing them exactly where they make the most sense contextually (e.g., placing a 'quiz' immediately after a difficult concept, or a 'video' before a new topic).\n"
            "4. A section node must be represented EXACTLY with the title formatted as '--------- [section_name]' (e.g., '--------- pre-requisites', '--------- quiz'). Do NOT include page numbers in section titles. CRITICAL: Sections are LEAF nodes. They MUST NEVER have 'children' or 'pages' arrays. NO treemap part should ever be nested under a section.\n"
            "5. CRITICAL: Do NOT omit any of the actual textbook headings/topics. The sections should be added IN ADDITION to the normal topics, so that all treemap parts are visible together with the sections.\n"
            "6. CRITICAL: You MUST place exactly one '--------- qualify' section as the absolute LAST element in the 'tree' array's children, signifying the end of the chapter.\n"
            "Return ONLY a JSON object with a 'tree' key containing an array of nodes. "
            "Each node should have 'title', 'pages' (array of integers, except for sections), and 'children' (array of nodes, except for sections) keys.\n\n"
            f"Analyses:\n{context}"
        )
        
        async def build_tree():
            try:
                # Use a separate LLM instance for tree generation to allow for larger token outputs if the chapter is very long
                tree_llm = ChatOpenAI(
                    model="google/gemma-4-26b-a4b-it",
                    openai_api_key=api_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                    max_tokens=4000
                )
                tree_res = await tree_llm.ainvoke([HumanMessage(content=tree_prompt)])
                
                if not tree_res or not tree_res.content:
                    print(f"No response from LLM for tree generation in {chapter['title']}")
                    tree_data = {'tree': []}
                else:
                    tree_content = tree_res.content.strip()
                    
                    json_match = re.search(r'\{.*\}', tree_content, re.DOTALL)
                    if json_match:
                        tree_content = json_match.group(0)
                    
                    try:
                        tree_data = json_repair.loads(tree_content)
                        if not isinstance(tree_data, dict):
                            tree_data = {'tree': []}
                    except Exception as e:
                        print(f"JSON parsing failed after json_repair: {e}")
                        tree_data = {'tree': []}
                
                if tree_data is None:
                    tree_data = {'tree': []}
                    
                chapter_tree = tree_data.get('tree', [])
                if chapter_tree is None:
                    chapter_tree = []
                chapter['original_tree'] = chapter_tree  # Save original tree before preprocessing
                
                # Do not remove redundant root node anymore as requested by user
                chapter['tree'] = chapter_tree
                chapter['status'] = 'completed'
            except Exception as e:
                print(f"Error generating tree for {chapter['title']}: {e}")
                chapter['tree'] = []
                chapter['status'] = 'failed'

            # Update chapters_data in DB
            db = db_session_factory()
            try:
                goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
                if goal:
                    chapters = json.loads(goal.chapters_data)
                    if not isinstance(chapters, list):
                        chapters = []
                    for c in chapters:
                        if str(c['id']) == str(chapter['id']):
                            c['tree'] = chapter.get('tree', [])
                            c['original_tree'] = chapter.get('original_tree', [])
                            c['status'] = 'completed'
                            c['page_summaries'] = page_summaries
                            break
                    goal.chapters_data = json.dumps(chapters)
                    db.commit()
            finally:
                db.close()

        def extract_vectors():
            from langchain_core.documents import Document
            filtered_docs = []
            start_page = chapter.get('start', 1)
            end_page = chapter.get('end', doc.page_count)
            for i in range(start_page - 1, end_page):
                page_text = doc[i].get_text()
                if page_text.strip():
                    filtered_docs.append(Document(page_content=page_text, metadata={"source": pdf_path, "page": i}))
            
            if filtered_docs:
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                chunks = text_splitter.split_documents(filtered_docs)
                if not chunks:
                    return
                try:
                    new_vs = FAISS.from_documents(chunks, embeddings_model)
                    
                    if not os.path.exists(vector_store_path):
                        os.makedirs(vector_store_path)
                        
                    import threading
                    faiss_lock = threading.Lock()
                    with faiss_lock:
                        if os.path.exists(os.path.join(vector_store_path, "index.faiss")):
                            existing_vs = FAISS.load_local(vector_store_path, embeddings_model, allow_dangerous_deserialization=True)
                            existing_vs.merge_from(new_vs)
                            existing_vs.save_local(vector_store_path)
                        else:
                            new_vs.save_local(vector_store_path)
                except TypeError as e:
                    if "NoneType" in str(e):
                        print(f"Embedding failed due to OpenRouter API error (TypeError: {e}). Skipping vector extraction for this chunk.")
                    else:
                        raise e
                except Exception as e:
                    print(f"Error extracting vectors: {e}")

        await asyncio.gather(
            build_tree(),
            asyncio.to_thread(extract_vectors)
        )
                
    finally:
        doc.close()

def process_remaining_chapters_task(goal_id: int, chapters: list, pdf_path: str, vector_store_path: str, db_session_factory):
    api_key = os.getenv("OPENROUTER_API_KEY")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Set status of remaining chapters to loading in DB
    db = db_session_factory()
    try:
        goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
        if goal:
            chapters_data = json.loads(goal.chapters_data)
            if not isinstance(chapters_data, list):
                chapters_data = []
            for chapter in chapters:
                for cd in chapters_data:
                    if str(cd['id']) == str(chapter['id']):
                        cd['status'] = 'loading'
                        break
            goal.chapters_data = json.dumps(chapters_data)
            db.commit()
    finally:
        db.close()

    for idx, chapter in enumerate(chapters):
        try:
            loop.run_until_complete(process_single_chapter(goal_id, chapter, pdf_path, vector_store_path, api_key, db_session_factory))
        except Exception as e:
            print(f"Error processing background chapter {chapter['title']}: {e}")
            
    # Check if goal still exists and is not failed before final completion status
    db = db_session_factory()
    try:
        goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
        if goal and goal.status != "failed":
            goal.status = "completed"
            goal.status_message = "All selected chapters processed and ready!"
            db.commit()
    finally:
        db.close()
    loop.close()

def process_pdf_to_faiss_task(goal_id: int, pdf_path: str, vector_store_path: str, db_session_factory):
    # This is now handled more granularly, but keeping the name for compatibility if needed elsewhere
    pass

# Dependency to get current user from cookie
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        # Check if token starts with Bearer
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        user = auth.get_current_user(token, db)
        return user
    except HTTPException:
        return None

def require_user(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    if user.onboarding_completed:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="onboarding.html")

@app.post("/api/onboarding")
async def complete_onboarding(
    data: schemas.OnboardingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    current_user.level = data.level
    current_user.objectives = data.objectives
    current_user.onboarding_completed = True
    db.commit()
    return {"message": "Onboarding completed"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    if not user.onboarding_completed:
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # We pass the API key to the template if needed for client-side stuff, 
    # but here we mostly use it on the server.
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"user": user}
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_portal(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    users = db.query(models.User).all()
    return templates.TemplateResponse(
        request=request, name="admin.html", context={"user": user, "users": users}
    )

@app.post("/api/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Auto login
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    
    return new_user

@app.post("/api/login")
def login(user: schemas.UserCreate, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {"message": "Login successful"}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}

@app.get("/api/goals", response_model=list[schemas.GoalResponse])
def get_goals(db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    goals = db.query(models.Goal).filter(models.Goal.owner_id == current_user.id).order_by(models.Goal.id.desc()).all()
    return goals

@app.patch("/api/goals/{goal_id}", response_model=schemas.GoalResponse)
def update_goal(
    goal_id: int,
    goal_update: schemas.GoalUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if goal_update.title is not None:
        goal.title = goal_update.title
    if goal_update.description is not None:
        goal.description = goal_update.description
    
    db.commit()
    db.refresh(goal)
    return goal

@app.delete("/api/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Cleanup files
    try:
        if goal.pdf_path:
            # pdf_path is /static/uploads/...
            actual_pdf_path = goal.pdf_path.lstrip("/")
            if os.path.exists(actual_pdf_path):
                os.remove(actual_pdf_path)
        
        if goal.vector_store_path and os.path.exists(goal.vector_store_path):
            shutil.rmtree(goal.vector_store_path)
    except Exception as e:
        print(f"Error cleaning up files for goal {goal_id}: {e}")

    db.delete(goal)
    db.commit()
    return {"message": "Goal deleted successfully"}

@app.post("/api/goals", response_model=schemas.GoalResponse)
async def create_goal(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    # Validate file size (max 50MB)
    MAX_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    
    # Save file
    import time
    timestamp = int(time.time())
    unique_filename = f"{current_user.id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Setup vector store path
    vector_store_name = f"vs_{current_user.id}_{timestamp}"
    vector_store_path = os.path.join(VECTOR_DIR, vector_store_name)
    
    new_goal = models.Goal(
        title=title,
        description=description,
        pdf_path=f"/static/uploads/{unique_filename}",
        vector_store_path=vector_store_path,
        status="processing",
        status_message="Starting background processing...",
        owner_id=current_user.id
    )
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    
    from .database import SessionLocal
    background_tasks.add_task(extract_toc_task, new_goal.id, file_path, title, description or "", SessionLocal)
    
    return new_goal

@app.post("/api/goals/{goal_id}/select_chapters")
async def select_chapters(
    goal_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    data = await request.json()
    
    all_selected = []
    for c in data.get("chapters", []):
        if isinstance(c, dict) and c.get('selected'):
            all_selected.append(c)
    
    if not all_selected:
        raise HTTPException(status_code=400, detail="No chapters selected")
    
    # Update chapters_data with user selection (all selected chapters)
    goal.chapters_data = json.dumps(all_selected)
    goal.status = "processing"
    goal.status_message = f"Processing first chapter: {all_selected[0]['title']}..."
    db.commit()
    db.refresh(goal)
    
    actual_pdf_path = goal.pdf_path.lstrip("/")
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Process the first chapter immediately (but still in a task-like way within this request)
    # Actually, we should use background_tasks for the first one too but wait for it or just 
    # make this endpoint async and await the first chapter.
    
    from .database import SessionLocal
    
    async def process_first_and_queue_rest(goal_id, chapters_to_process, pdf_path, vector_store_path, api_key):
        try:
            # Mark first chapter as loading
            db = SessionLocal()
            try:
                goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
                if goal and goal.chapters_data:
                    chapters_data = json.loads(goal.chapters_data)
                    if chapters_data and isinstance(chapters_data, list):
                        # Mark all as pending/loading initially
                        for c in chapters_data:
                            if isinstance(c, dict):
                                c['status'] = 'loading'
                        goal.chapters_data = json.dumps(chapters_data)
                        db.commit()
            finally:
                db.close()

            # 1. Process the first chapter
            first_chapter = chapters_to_process[0]
            await process_single_chapter(goal_id, first_chapter, pdf_path, vector_store_path, api_key, SessionLocal)
            
            # 2. Set status to completed so user can start chatting
            update_goal_status(goal_id, "completed", f"First chapter '{first_chapter['title']}' ready! Incremental map is building...", SessionLocal)
            
            # 3. Queue remaining chapters if any
            if len(chapters_to_process) > 1:

                import threading
                thread = threading.Thread(
                    target=process_remaining_chapters_task,
                    args=(goal_id, chapters_to_process[1:], pdf_path, vector_store_path, SessionLocal)
                )
                thread.start()
        except Exception as e:
            import traceback
            traceback.print_exc()
            update_goal_status(goal_id, "failed", f"Error processing first chapter: {str(e)}", SessionLocal)

    background_tasks.add_task(process_first_and_queue_rest, goal.id, all_selected, actual_pdf_path, goal.vector_store_path, api_key)
    
    return {"message": "Processing started. You will be able to chat as soon as the first chapter is ready."}


@app.get("/api/goals/{goal_id}", response_model=schemas.GoalResponse)
def get_goal_status(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@app.get("/api/goals/{goal_id}/quizzes", response_model=list[schemas.QuizResponse])
def get_quizzes(
    goal_id: int,
    chapter_title: str = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    query = db.query(models.Quiz).filter(models.Quiz.goal_id == goal_id)
    if chapter_title:
        # Search for chapter_title in the quiz title or content
        query = query.filter(models.Quiz.title.ilike(f"%{chapter_title}%"))
        
    quizzes = query.order_by(models.Quiz.id.desc()).all()
    return quizzes

@app.post("/api/quizzes/{quiz_id}/attempts", response_model=schemas.QuizAttemptResponse)
def submit_quiz_attempt(
    quiz_id: int,
    attempt: schemas.QuizAttemptBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    goal = db.query(models.Goal).filter(models.Goal.id == quiz.goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    new_attempt = models.QuizAttempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        score=attempt.score,
        total=attempt.total,
        answers=attempt.answers,
        completed=attempt.completed
    )
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    return new_attempt

@app.get("/api/goals/{goal_id}/flashcards", response_model=list[schemas.FlashcardSetResponse])
def get_flashcards(
    goal_id: int,
    chapter_title: str = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    query = db.query(models.FlashcardSet).filter(models.FlashcardSet.goal_id == goal_id)
    if chapter_title:
        query = query.filter(models.FlashcardSet.title.ilike(f"%{chapter_title}%"))

    fc = query.order_by(models.FlashcardSet.id.desc()).all()
    return fc

@app.get("/api/goals/{goal_id}/chat", response_model=list[schemas.ChatMessageResponse])
def get_chat_history(
    goal_id: int,
    chapter_title: str = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    q = db.query(models.ChatMessage).filter(models.ChatMessage.goal_id == goal_id)
    if chapter_title:
        q = q.filter(models.ChatMessage.chapter_title == chapter_title)
    else:
        q = q.filter(models.ChatMessage.chapter_title == None)
        
    messages = q.order_by(models.ChatMessage.id.asc()).all()
    return messages



@app.get("/api/goals/{goal_id}/qualify_questions")
def get_qualify_questions(
    goal_id: int, 
    chapter_title: str = Query(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    chapters = json.loads(goal.chapters_data) if goal.chapters_data else []
    chapter = next((c for c in chapters if c['title'] == chapter_title), None)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    summaries = chapter.get('page_summaries', [])
    context = "\n".join([f"Page {s['page_number']}: {s['analysis']}" for s in summaries])
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=1000
    )
    prompt = (
        f"Based on the following chapter summaries, generate exactly 10 distinct and diverse questions that test the user's knowledge of the core concepts in this chapter. "
        f"You MUST include exactly these kinds of questions: "
        f"3 Factual/Recall questions (testing basic knowledge), "
        f"3 Conceptual/Reasoning questions (testing understanding of principles), "
        f"2 Application/Problem-solving questions (applying concepts to scenarios), "
        f"and 2 Analytical questions (comparing or contrasting different ideas). "
        f"Prefix each question with its type, for example: '[Factual] What is...'. "
        f"Return ONLY a JSON list of strings representing the questions, nothing else.\n\n"
        f"Summaries:\n{context}"
    )
    
    # We use a synchronous invoke since it's a def (sync) endpoint. We can just use the sync invoke of ChatOpenAI.
    # But wait, ChatOpenAI invoke is sync. That's fine.
    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        content = res.content.strip()
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        questions = json_repair.loads(content)
        if not isinstance(questions, list):
            questions = []
    except Exception as e:
        print(f"Error generating qualify questions: {e}")
        questions = []
        
    return {"questions": questions}

@app.post("/api/goals/{goal_id}/score_qualify")
async def score_qualify(
    goal_id: int, 
    questions: str = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(require_user)
):
    import base64
    from langchain_core.messages import HumanMessage
    
    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Max 10 images allowed")
        
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    content = [{"type": "text", "text": f"Here are 10 questions:\n{questions}\n\nAnd here are images of handwritten responses. Please read the handwritten responses and grade them out of 10. Give 1 point for each question correctly or reasonably answered. Return ONLY a JSON object with a single key 'score' containing an integer between 0 and 10, nothing else."}]
    
    for img in images:
        img_bytes = await img.read()
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        mime_type = img.content_type or "image/jpeg"
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
        })
        
    api_key = os.getenv("OPENROUTER_API_KEY")
    vision_llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=500
    )
    
    try:
        res = await vision_llm.ainvoke([HumanMessage(content=content)])
        json_str = res.content.strip()
        json_str = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'^```\s*', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'\s*```$', '', json_str, flags=re.MULTILINE)
        
        data = json_repair.loads(json_str)
        score = int(data.get("score", 0))
    except Exception as e:
        print(f"Error scoring qualify images: {e}")
        score = 0
        
    return {"score": score}

async def search_youtube_videos(query: str):
    api_key = os.getenv("YOUTUBE_DATA_API_KEY")
    if not api_key:
        return []
    
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": 3,
        "type": "video",
        "key": api_key
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                videos = []
                for item in data.get("items", []):
                    videos.append({
                        "title": item["snippet"]["title"],
                        "video_id": item["id"]["videoId"],
                        "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"]
                    })
                return videos
        except Exception as e:
            print(f"YouTube API Error: {e}")
    return []

@app.post("/api/goals/{goal_id}/videos")
async def generate_videos(
    goal_id: int,
    term: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Check if we already have videos for this term
    existing = db.query(models.VideoSuggestion).filter(
        models.VideoSuggestion.goal_id == goal_id,
        models.VideoSuggestion.term == term
    ).first()
    
    if existing:
        return existing
    
    videos = await search_youtube_videos(term)
    
    new_suggestion = models.VideoSuggestion(
        goal_id=goal_id,
        term=term,
        video_data=json.dumps(videos)
    )
    db.add(new_suggestion)
    db.commit()
    db.refresh(new_suggestion)
    return new_suggestion

@app.get("/api/goals/{goal_id}/videos", response_model=list[schemas.VideoSuggestionResponse])
def get_videos(
    goal_id: int,
    chapter_title: str = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    query = db.query(models.VideoSuggestion).filter(models.VideoSuggestion.goal_id == goal_id)
    if chapter_title:
        query = query.filter(models.VideoSuggestion.term.ilike(f"%{chapter_title}%"))

    videos = query.order_by(models.VideoSuggestion.id.desc()).all()
    return videos

@app.get("/api/goals/{goal_id}/visuals", response_model=list[schemas.VisualResponse])
def get_visuals(
    goal_id: int,
    chapter_title: str = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    query = db.query(models.Visual).filter(models.Visual.goal_id == goal_id)
    if chapter_title:
        query = query.filter(models.Visual.term.ilike(f"%{chapter_title}%"))

    visuals = query.order_by(models.Visual.id.desc()).all()
    return visuals

@app.get("/api/goals/{goal_id}/topics/{topic_name}/description", response_model=schemas.TopicDescriptionResponse)
def get_topic_description(
    goal_id: int,
    topic_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    desc = db.query(models.TopicDescription).filter(
        models.TopicDescription.goal_id == goal_id,
        models.TopicDescription.topic_name == topic_name
    ).first()
    
    if not desc:
        raise HTTPException(status_code=404, detail="Description not found")
    
    return desc

@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    return templates.TemplateResponse(request=request, name="test.html")

@app.post("/api/analyze-page")
async def analyze_page(data: dict):
    page_number = data.get("page_number")
    content = data.get("content")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=1000
    )
    
    prompt = (
        f"Analyze the following text from page {page_number} of a textbook. "
        "Describe in detail what this page contains (e.g., definitions, explanations, worked examples, diagrams, etc.). "
        "CRITICAL: Always identify and include information about any headings, titles, subheadings, or subtitles found on this page. "
        "Talk about what they signify and mean in the context of the page. Provide a concise but detailed summary. "
        "CRITICAL: The summary must NOT exceed 150 words.\n\n"
        f"Content:\n{content}"
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"page_number": page_number, "analysis": response.content}

@app.post("/api/generate-tree")
async def generate_tree(data: dict):
    summaries = data.get("summaries", [])
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=2000
    )
    
    context = "\n".join([f"Page {s['page_number']}: {s['analysis']}" for s in summaries])
    
    prompt = (
        "Based on the following page-by-page analyses, create a hierarchical tree of chapters, subchapters, and topics (subsubchapters). "
        "CRITICAL: The tree MUST be built strictly using the actual headings, titles, subheadings, and subtitles found in the analyses. Do not invent topics; use the exact wording of the headings identified in the text. "
        "IMPORTANT: For each chapter, subchapter, or topic, you MUST include the relevant page number(s) in the title (e.g. 'Chapter 1: Introduction (Page 1)'). "
        "Return ONLY a JSON object with a 'tree' key containing an array of nodes. "
        "Each node should have 'title' and 'children' (array of nodes) keys.\n\n"
        f"Analyses:\n{context}"
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
    
    try:
        tree_data = json_repair.loads(content)
        if not isinstance(tree_data, dict):
            raise ValueError()
        return tree_data
    except:
        # Fallback
        return {"tree": [{"title": "Document", "children": [{"title": "All Content", "children": []}]}]}

@app.post("/api/suggestions")
async def get_suggestions(
    goal_id: int = Form(...),
    chapter_title: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    query = db.query(models.ChatMessage).filter(models.ChatMessage.goal_id == goal_id)
    if chapter_title:
        query = query.filter(models.ChatMessage.chapter_title == chapter_title)
    
    history = query.order_by(models.ChatMessage.id.desc()).limit(6).all()
    history = history[::-1]

    if not history:
        context_msg = f" for the chapter '{chapter_title}'" if chapter_title else ""
        return [
            f"What are the main concepts discussed in this document{context_msg}?",
            "3@quiz Generate quizzes based on the key topics",
            "5@flashcard Generate flashcards for the important terms",
            "Can you provide a summary of the most important points?",
            "@video Find a video explaining the core concepts"
        ]

    chat_context = ""
    for m in history:
        content = m.content
        if ";;;;;" in content:
            content = content.split(";;;;;")[0].strip()
        chat_context += f"{m.role.upper()}: {content}\n"

    chapter_info = f"The user is currently studying the chapter: '{chapter_title}'.\n" if chapter_title else ""
    
    prompt = (
        f"You are a helpful learning assistant. Based on the recent chat history and current context below, generate 4 short, highly contextual follow-up suggestions for the student. "
        f"The suggestions must be directly related to the topics currently being discussed and the specific chapter context. Avoid generic phrases. "
        f"Rules:\n"
        f"1. Suggestion 1: A specific follow-up question deepening the current topic (normal query).\n"
        f"2. Suggestion 2: A video search proposal starting with '@video ' followed by a specific concept from the last AI response.\n"
        f"3. Suggestion 3: A flashcard proposal starting with '5@flashcard ' followed by specific key terms from the last AI response.\n"
        f"4. Suggestion 4: A quiz proposal starting with '3@quiz ' followed by a specific concept from the last AI response.\n"
        f"Output ONLY a JSON list of 4 strings. No other text.\n\n"
        f"Current Context:\n{chapter_info}"
        f"Recent Chat History:\n{chat_context}"
    )

    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=500
    )

    try:
        res = await llm.ainvoke([HumanMessage(content=prompt)])
        content = res.content.strip()
        # Clean up JSON if necessary
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        
        suggestions = json.loads(content)
        if isinstance(suggestions, list) and len(suggestions) >= 5:
            # Save suggestions to the last AI message in the DB
            last_msg = db.query(models.ChatMessage).filter(models.ChatMessage.goal_id == goal_id, models.ChatMessage.role == "ai").order_by(models.ChatMessage.id.desc()).first()
            if last_msg:
                last_msg.suggestions = json.dumps(suggestions[:5])
                db.commit()
            return suggestions[:5]
    except Exception as e:
        print(f"Error generating suggestions: {e}")
    
    # Fallback if LLM fails
    return [
        "Can you explain that in more detail?",
        "3@quiz Generate a quiz on this topic",
        "5@flashcard Create flashcards for this",
        "What are the practical applications of this?"
    ]

@app.post("/api/chat")
async def chat_with_ai(
    message: str = Form(...), 
    goal_id: int = Form(...),
    chapter_title: str = Form(None),
    image_data: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.owner_id == current_user.id).first()
    if not goal or not goal.vector_store_path:
        raise HTTPException(status_code=404, detail="Goal or vector store not found")

    if goal.status != "completed":
        raise HTTPException(status_code=400, detail=f"Goal is not ready yet. Current status: {goal.status} - {goal.status_message}")

    if not os.path.exists(goal.vector_store_path):
        raise HTTPException(status_code=500, detail="Vector store missing on disk")

    try:
        # 1. Retrieve context
        vector_store = FAISS.load_local(goal.vector_store_path, embeddings_model, allow_dangerous_deserialization=True)
        docs = vector_store.similarity_search(message, k=8)
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            context_parts.append(f"[Snippet {i}]\n{doc.page_content}")
        context = "\n\n".join(context_parts)

        # 2. Run LangGraph
        
        # Parse message type from prefix if present
        msg_type = "text"
        if "@quiz" in message:
            msg_type = "quiz"
        elif "@flashcard" in message:
            msg_type = "flashcard"
        elif "@summary" in message:
            msg_type = "summary"
        elif "@video" in message:
            msg_type = "video"
        elif "@visual" in message or "visual" in message.lower():
            msg_type = "visual"
            
        is_json_task = msg_type in ["quiz", "flashcard"]
        is_html_task = msg_type == "visual"
        
        # Save user message
        user_msg = models.ChatMessage(goal_id=goal_id, chapter_title=chapter_title, role="user", content=message, msg_type=msg_type)
        db.add(user_msg)
        db.commit()

        # Create AI message placeholder
        ai_msg = models.ChatMessage(goal_id=goal_id, chapter_title=chapter_title, role="ai", content="", msg_type=msg_type)
        db.add(ai_msg)
        db.commit()
        db.refresh(ai_msg)

        if msg_type == "video":
            term = re.sub(r'^\d*@video\s*', '', message, flags=re.IGNORECASE).strip()
            if not term:
                term = message.replace("@video", "").strip()
            
            if len(term.split()) > 11:
                summarize_llm = ChatOpenAI(
                    model="google/gemma-4-26b-a4b-it",
                    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                    openai_api_base="https://openrouter.ai/api/v1",
                    temperature=0.3
                )
                try:
                    summary_res = summarize_llm.invoke(f"Summarize the following into a search query of fewer than 12 words:\n\n{term}")
                    term = summary_res.content.strip()
                except Exception:
                    term = " ".join(term.split()[:11])
                    
            ai_msg.content = f"I've found some videos for **{term}**. You can view them in the Videos tab."
            db.commit()

            # Search youtube
            existing = db.query(models.VideoSuggestion).filter(
                models.VideoSuggestion.goal_id == goal_id,
                models.VideoSuggestion.term == term
            ).first()
            if not existing:
                videos = await search_youtube_videos(term)
                video_term = term
                if chapter_title and chapter_title not in video_term:
                    video_term = f"{chapter_title}: {video_term}"
                new_suggestion = models.VideoSuggestion(
                    goal_id=goal_id,
                    term=video_term,
                    video_data=json.dumps(videos)
                )
                db.add(new_suggestion)
                db.commit()
            
            async def generate():
                yield ai_msg.content
                
            return StreamingResponse(
                generate(), 
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        # Retrieve full history from DB to pass to LLM
        q = db.query(models.ChatMessage).filter(models.ChatMessage.goal_id == goal_id)
        if chapter_title:
            q = q.filter(models.ChatMessage.chapter_title == chapter_title)
        else:
            q = q.filter(models.ChatMessage.chapter_title == None)
        history = q.order_by(models.ChatMessage.id.asc()).all()
        
        # Build messages for LangGraph
        langchain_messages = []
        for h in history[:-1]:
            if h.role == "user":
                langchain_messages.append(HumanMessage(content=h.content))
            elif h.role == "ai":
                if h.content:
                    langchain_messages.append(AIMessage(content=h.content))
                    
        # Append the new message
        if image_data and image_data.startswith("data:image"):
            langchain_messages.append(HumanMessage(content=[
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]))
        else:
            langchain_messages.append(HumanMessage(content=message))

        initial_state = {
            "messages": langchain_messages,
            "context": context
        }
        
        queue = asyncio.Queue()
        stop_event = asyncio.Event()
        app.state.active_generators = getattr(app.state, 'active_generators', {})
        app.state.active_generators[goal_id] = stop_event

        async def run_model():
            current_state = initial_state
            max_retries = 3
            success = False
            full_content = ""
            
            for attempt in range(max_retries):
                if stop_event.is_set():
                    break
                full_content = ""
                try:
                    if not is_json_task:
                        # Stream normally for text and HTML
                        async for chunk, metadata in rag_agent.astream(current_state, stream_mode="messages"):
                            if stop_event.is_set():
                                break
                            if isinstance(chunk, AIMessage):
                                chunk_content = chunk.content
                                if chunk_content:
                                    full_content += chunk_content
                                    await queue.put(chunk_content)
                        success = not stop_event.is_set()
                        break
                    else:
                        # For JSON tasks, block and await the full response to validate
                        await queue.put(f"Generating items (Attempt {attempt + 1}/{max_retries})...\n")
                        if stop_event.is_set():
                            break
                        # we can't easily interrupt an ainovke cleanly without modifying the langgraph execution deeply
                        # but we will check immediately after
                        result = await rag_agent.ainvoke(current_state)
                        if stop_event.is_set():
                            break
                        full_content = result["messages"][-1].content
                        
                        # Validate JSON
                        json_str = full_content.strip()
                        json_str = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
                        json_str = re.sub(r'^```\s*', '', json_str, flags=re.MULTILINE)
                        json_str = re.sub(r'\s*```$', '', json_str, flags=re.MULTILINE)
                        
                        start_idx = min(json_str.find('{') if '{' in json_str else float('inf'), json_str.find('[') if '[' in json_str else float('inf'))
                        end_idx = max(json_str.rfind('}') if '}' in json_str else -1, json_str.rfind(']') if ']' in json_str else -1)
                        
                        if start_idx == float('inf') or end_idx == -1:
                            raise ValueError("No JSON object or array found in response")
                            
                        json_str = json_str[int(start_idx):end_idx+1]
                        
                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError as e:
                            json_str_fixed = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', json_str)
                            try:
                                data = json.loads(json_str_fixed)
                            except json.JSONDecodeError as fixed_e:
                                raise ValueError(f"JSON Decode Error: {str(e)}. Attempted fix failed with: {str(fixed_e)}")
                        
                        success = True
                        break
                        
                except Exception as e:
                    error_msg = f"\nValidation failed: {str(e)}\n"
                    print(error_msg)
                    if attempt < max_retries - 1:
                        await queue.put("Validation failed. Retrying...\n")
                        # Append the failure to the state messages to guide the LLM
                        current_state["messages"] = current_state["messages"] + [
                            AIMessage(content=full_content),
                            HumanMessage(content=f"Your previous response failed validation with error: {str(e)}. Please correct the JSON formatting. Remember to double-escape backslashes in LaTeX formulas (e.g. \\\\alpha) and ensure the output is exclusively valid JSON.")
                        ]
                    else:
                        error_msg = f"\n\nMax retries reached. Final Error: {str(e)}"
                        full_content += error_msg
                        await queue.put(error_msg)
            
            await queue.put(None) # EOF

            # Save to DB using a new session
            from .database import SessionLocal
            db2 = SessionLocal()
            try:
                msg = db2.query(models.ChatMessage).filter(models.ChatMessage.id == ai_msg.id).first()
                if msg:
                    if msg.msg_type == "quiz" and success and 'data' in locals():
                        try:
                            if not isinstance(data, list):
                                data = [data]
                                
                            quiz_ids = []
                            for item in data:
                                if not isinstance(item, dict): continue
                                quiz_title = item.get("title", "Generated Quiz")
                                if msg.chapter_title and msg.chapter_title not in quiz_title:
                                    quiz_title = f"{msg.chapter_title}: {quiz_title}"
                                new_quiz = models.Quiz(
                                    goal_id=msg.goal_id,
                                    title=quiz_title,
                                    questions=json.dumps(item.get("questions", []))
                                )
                                db2.add(new_quiz)
                                db2.flush()
                                quiz_ids.append(new_quiz.id)
                            
                            if quiz_ids:
                                msg.related_id = quiz_ids[0] # Link to the first one for now
                                msg.content = f"{len(quiz_ids)} Quiz(zes) generated successfully! Please check the Quizzes section."
                            else:
                                msg.content = full_content
                        except Exception as e:
                            print("Failed to save quiz to DB:", e)
                            msg.content = full_content
                    elif msg.msg_type == "flashcard" and success and 'data' in locals():
                        try:
                            if not isinstance(data, list):
                                data = [data]
                                
                            fc_ids = []
                            for item in data:
                                if not isinstance(item, dict): continue
                                fc_title = item.get("title", "Generated Flashcards")
                                if msg.chapter_title and msg.chapter_title not in fc_title:
                                    fc_title = f"{msg.chapter_title}: {fc_title}"
                                new_fc = models.FlashcardSet(
                                    goal_id=msg.goal_id,
                                    title=fc_title,
                                    cards=json.dumps(item.get("cards", []))
                                )
                                db2.add(new_fc)
                                db2.flush()
                                fc_ids.append(new_fc.id)
                            
                            if fc_ids:
                                msg.related_id = fc_ids[0]
                                msg.content = f"{len(fc_ids)} Flashcard set(s) generated successfully! Please check the Flashcards section."
                            else:
                                msg.content = full_content
                        except Exception as e:
                            print("Failed to save flashcards to DB:", e)
                            msg.content = full_content
                    elif msg.msg_type == "visual" and success:
                        try:
                            term = "Generated Visual"
                            # Try to extract term from HTML comment: <!-- TERM: Concept Name -->
                            match = re.search(r'<!--\s*TERM:\s*(.*?)\s*-->', full_content, re.IGNORECASE)
                            if match:
                                term = match.group(1).strip()
                            
                            match_html = re.search(r'```(?:html)?\s*(.*?)\s*```', full_content, re.IGNORECASE | re.DOTALL)
                            if match_html:
                                html_str = match_html.group(1).strip()
                            else:
                                html_str = full_content.strip()
                                html_str = re.sub(r'^```html\s*', '', html_str, flags=re.IGNORECASE|re.MULTILINE)
                                html_str = re.sub(r'^```\s*', '', html_str, flags=re.MULTILINE)
                                html_str = re.sub(r'\s*```$', '', html_str, flags=re.MULTILINE)
                            
                            vis_term = term
                            if msg.chapter_title and msg.chapter_title not in vis_term:
                                vis_term = f"{msg.chapter_title}: {vis_term}"
                            new_vis = models.Visual(
                                goal_id=msg.goal_id,
                                term=vis_term,
                                html_content=html_str
                            )
                            db2.add(new_vis)
                            db2.flush()
                            msg.related_id = new_vis.id
                            msg.content = full_content
                        except Exception as e:
                            print("Failed to save visual to DB:", e)
                            msg.content = full_content
                    else:
                        msg.content = full_content
                    db2.commit()
            finally:
                db2.close()

        run_task = asyncio.create_task(run_model())
        
        app.state.active_tasks = getattr(app.state, 'active_tasks', {})
        app.state.active_tasks[goal_id] = run_task

        async def generate():
            try:
                while True:
                    if stop_event.is_set():
                        break
                    try:
                        # use wait_for so we can periodically check stop_event
                        chunk = await asyncio.wait_for(queue.get(), timeout=1.0)
                        if chunk is None:
                            break
                        yield chunk
                    except asyncio.TimeoutError:
                        continue
            finally:
                if goal_id in getattr(app.state, 'active_generators', {}):
                    del app.state.active_generators[goal_id]
                
        return StreamingResponse(
            generate(), 
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
