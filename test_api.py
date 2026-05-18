import requests
import io

def test_api():
    # 1. Login
    session = requests.Session()
    res = session.post("http://127.0.0.1:8000/api/login", json={"email": "folefac@test.com", "password": "password"})
    print("Login:", res.status_code, res.text)
    
    # Try signup if login fails
    if res.status_code != 200:
        res = session.post("http://127.0.0.1:8000/api/signup", json={"email": "folefac@test.com", "password": "password"})
        print("Signup:", res.status_code, res.text)
        
    # 2. Get goals
    res = session.get("http://127.0.0.1:8000/api/goals")
    print("Goals:", res.status_code, res.text)
    
    goals = res.json()
    if not goals:
        print("Creating goal...")
        from reportlab.pdfgen import canvas
        pdf_file = io.BytesIO()
        c = canvas.Canvas(pdf_file)
        c.drawString(100, 750, "Hello World from test PDF")
        c.save()
        pdf_file.seek(0)
        
        files = {"file": ("test.pdf", pdf_file, "application/pdf")}
        data = {"title": "Test Goal", "description": "Testing"}
        res = session.post("http://127.0.0.1:8000/api/goals", files=files, data=data)
        print("Create Goal:", res.status_code, res.text)
        goals = [res.json()]
        
    if goals and 'id' in goals[0]:
        goal_id = goals[0]["id"]
        # 3. Chat
        res = session.post("http://127.0.0.1:8000/api/chat", data={"message": "What does the pdf say?", "goal_id": goal_id})
        print("Chat:", res.status_code, res.text)

if __name__ == "__main__":
    test_api()