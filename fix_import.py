with open('app/main.py', 'r') as f:
    content = f.read()

content = content.replace(
    "from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, File, UploadFile, Form, BackgroundTasks",
    "from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, File, UploadFile, Form, BackgroundTasks, Query"
)

with open('app/main.py', 'w') as f:
    f.write(content)
