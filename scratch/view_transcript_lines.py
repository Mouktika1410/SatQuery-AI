import json

path = r'C:\Users\Mouktika\.gemini\antigravity\brain\32c86eee-39a7-4298-b704-22c9f3030575\.system_generated\logs\transcript.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 5220 <= i <= 5265:
            obj = json.loads(line)
            if obj.get('type') == 'USER_INPUT':
                print(f"=== User input at {i} ===")
                print(obj.get('content'))
                print("========================\n")
            elif 'INITIAL MAP' in str(obj):
                print(f"Match INITIAL MAP at {i}, type={obj.get('type')}")
                print(str(obj.get('thinking', ''))[:400])
