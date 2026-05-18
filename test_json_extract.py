
import json
import re

def extract_json(full_content):
    json_str = full_content.strip()
    # Extra clean-up for the model response
    json_str = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'^```\s*', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'\s*```$', '', json_str, flags=re.MULTILINE)
    
    # Extract JSON substring
    start_idx = min(json_str.find('{') if '{' in json_str else float('inf'), json_str.find('[') if '[' in json_str else float('inf'))
    end_idx = max(json_str.rfind('}') if '}' in json_str else -1, json_str.rfind(']') if ']' in json_str else -1)
    
    if start_idx != float('inf') and end_idx != -1:
        json_str = json_str[int(start_idx):end_idx+1]
        
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str_fixed = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', json_str)
        return json.loads(json_str_fixed)

def test_single_object():
    content = """
Here is your quiz:
```json
{
  "title": "Single Quiz",
  "questions": []
}
```
"""
    data = extract_json(content)
    assert isinstance(data, dict)
    assert data['title'] == "Single Quiz"
    print("test_single_object passed")

def test_list_objects():
    content = """
Here are 2 quizzes:
```json
[
  {
    "title": "Quiz 1",
    "questions": []
  },
  {
    "title": "Quiz 2",
    "questions": []
  }
]
```
"""
    data = extract_json(content)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['title'] == "Quiz 1"
    assert data[1]['title'] == "Quiz 2"
    print("test_list_objects passed")

def test_invalid_escape():
    # Simulate a JSON with an invalid escape (LaTeX backslash)
    content = """
{
  "title": "Math Quiz",
  "questions": [
    {"question": "What is \\alpha?", "options": ["A", "B"], "correct_index": 0}
  ]
}
"""
    # This should fail with normal json.loads but pass with our fix
    json_str = content.strip()
    try:
        json.loads(json_str)
        assert False, "Should have failed without fix"
    except json.JSONDecodeError:
        pass
    
    # Apply fix logic
    json_str_fixed = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', json_str)
    data = json.loads(json_str_fixed)
    assert data['questions'][0]['question'] == "What is \\alpha?"
    print("test_invalid_escape passed")

if __name__ == "__main__":
    test_single_object()
    test_list_objects()
    test_invalid_escape()
    test_single_object()
    test_list_objects()
