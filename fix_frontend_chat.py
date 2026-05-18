import re

with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""            try:
                const res = await fetch(`/api/goals/${goal.id}/chat`);""",
"""            try {
                let chatUrl = `/api/goals/${goal.id}/chat`;
                if (window.__activeChapterTitle) {
                    chatUrl += `?chapter_title=${encodeURIComponent(window.__activeChapterTitle)}`;
                }
                const res = await fetch(chatUrl);"""
)

content = content.replace(
"""            const formData = new FormData();
            formData.append('goal_id', currentGoalId);
            formData.append('message', msgText);""",
"""            const formData = new FormData();
            formData.append('goal_id', currentGoalId);
            formData.append('message', msgText);
            if (window.__activeChapterTitle) {
                formData.append('chapter_title', window.__activeChapterTitle);
            }"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
