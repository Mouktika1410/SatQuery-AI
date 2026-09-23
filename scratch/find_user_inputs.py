import json

path = r'C:\Users\Mouktika\.gemini\antigravity\brain\32c86eee-39a7-4298-b704-22c9f3030575\.system_generated\logs\transcript.jsonl'
user_inputs = []
with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        try:
            obj = json.loads(line)
            if obj.get('type') == 'USER_INPUT':
                user_inputs.append((i, obj.get('content')))
        except:
            pass

for idx, content in user_inputs[-4:]:
    print(f"--- Line {idx} ---")
    print(content.encode('ascii', errors='replace').decode('ascii'))
    print()
