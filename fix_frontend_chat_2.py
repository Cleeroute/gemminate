import re

with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""            try {
                const formData = new FormData();
                formData.append('message', message);
                formData.append('goal_id', currentGoalId);
                if (actionType === 'visual' && currentImage) {""",
"""            try {
                const formData = new FormData();
                formData.append('message', message);
                formData.append('goal_id', currentGoalId);
                if (window.__activeChapterTitle) {
                    formData.append('chapter_title', window.__activeChapterTitle);
                }
                if (actionType === 'visual' && currentImage) {"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
