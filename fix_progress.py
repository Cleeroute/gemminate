with open('app/main.py', 'r') as f:
    content = f.read()

content = content.replace(
"""                if current_page_num % 5 == 0:
                    update_goal_status(goal_id, "processing", f"Analyzing chapter '{chapter['title']}': Page {current_page_num}/{total_pages}...", db_session_factory, log_entry={"chapter": chapter['title'], **summary_data})""",
"""                if current_page_num % 5 == 0:
                    rel_page = current_page_num - start_page + 1
                    update_goal_status(goal_id, "processing", f"Analyzing chapter '{chapter['title']}': Page {rel_page}/{total_pages}...", db_session_factory, log_entry={"chapter": chapter['title'], **summary_data})"""
)

with open('app/main.py', 'w') as f:
    f.write(content)
