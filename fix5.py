import re

with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""                const textSpan = document.createElement('span');
                textSpan.className = "text-sm text-gray-700 flex-1";
                textSpan.textContent = s.text;""",
"""                const textSpan = document.createElement('span');
                textSpan.className = "text-sm text-gray-700 flex-1 flex items-center";
                let displayText = s.text;
                let badgeHtml = '';
                const matchCommand = s.text.match(/^(\\d+)?@(quiz|flashcard|video|summary)\\s*(.*)$/i);
                if (matchCommand) {
                    const num = matchCommand[1] || '';
                    const cmd = matchCommand[2].toLowerCase();
                    const rest = matchCommand[3];
                    let badgeColor = 'bg-gray-100 text-gray-700';
                    if (cmd === 'video') badgeColor = 'bg-orange-100 text-orange-700 border border-orange-200';
                    else if (cmd === 'quiz') badgeColor = 'bg-blue-100 text-blue-700 border border-blue-200';
                    else if (cmd === 'flashcard') badgeColor = 'bg-purple-100 text-purple-700 border border-purple-200';
                    else if (cmd === 'summary') badgeColor = 'bg-green-100 text-green-700 border border-green-200';
                    
                    badgeHtml = `<span class="px-2 py-0.5 rounded-md text-xs font-bold ${badgeColor} mr-2">${num ? num + '@' : '@'}${cmd}</span>`;
                    displayText = rest;
                }
                textSpan.innerHTML = badgeHtml + `<span>${escapeHtml(displayText)}</span>`;"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
