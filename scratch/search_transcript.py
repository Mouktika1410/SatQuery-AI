import json

path = r'C:\Users\Mouktika\.gemini\antigravity\brain\32c86eee-39a7-4298-b704-22c9f3030575\.system_generated\logs\transcript.jsonl'
keywords = ['SOUTH INDIA', 'INITIAL MAP', 'DETECTION ANIMATION', 'POLYGON REVEAL', 'LAYER REVEAL', 'REPLAY SEQUENCE', 'SATELLITETRANSITION']

with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        up = line.upper()
        for kw in keywords:
            if kw in up:
                print(f"Match '{kw}' at line {i}")
                try:
                    obj = json.loads(line)
                    content = str(obj.get('content', ''))[:300]
                    print(f"  Type: {obj.get('type')}, Content: {content}\n")
                except:
                    print(f"  Raw: {line[:200]}\n")
                break
