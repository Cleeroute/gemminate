with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""        window.__activeChapterTitle = currentChapterTitle || goal.title;""",
"""        if (!window.__activeChapterTitle || !window.__activeGoalId || window.__activeGoalId !== goal.id) {
            window.__activeChapterTitle = currentChapterTitle || goal.title;
            window.__activeGoalId = goal.id;
        }"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
