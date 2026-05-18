with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""                chapterHeader.onclick = () => {
                    highlightInPdf(chapter.title);
                    window.__activeChapterTitle = chapter.title;
                    if (activeGoal) showGoalContent(activeGoal, false);
                };""",
"""                chapterHeader.onclick = () => {
                    highlightInPdf(chapter.title);
                    window.__activeChapterTitle = chapter.title;
                    window.__activeGoalId = activeGoal ? activeGoal.id : null;
                    if (activeGoal) showGoalContent(activeGoal, false);
                };"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
