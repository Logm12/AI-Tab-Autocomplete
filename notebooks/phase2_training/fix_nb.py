import json
import os

nb_path = r'e:\Học hành\Viettel\AI-Auto-Complete\notebooks\phase2_training\04_generate_dpo_data.ipynb'

if not os.path.exists(nb_path):
    print(f"Error: path {nb_path} does not exist")
    exit(1)

print(f"Reading {nb_path}...")
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

patched = False
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source_text = "".join(cell['source'])
        if "def load_fim_samples" in source_text and "def extract_prompt_from_fim" in source_text:
            print("Found target cell.")
            new_source = []
            for line in cell['source']:
                if "if 'text' in data and '<fim_middle>' in data['text']:" in line:
                     print("Patching load_fim_samples condition...")
                     indent = line[:line.find("if")]
                     new_source.append(indent + "text = data.get('text', '')\n")
                     new_source.append(indent + "if '<fim_middle>' in text or '<MID>' in text:\n")
                elif "return parts[0] + '<fim_middle>'" in line:
                     print("Patching extract_prompt_from_fim logic...")
                     new_source.append(line)
                     new_source.append("    if '<MID>' in fim_text:\n")
                     new_source.append("        parts = fim_text.split('<MID>')\n")
                     new_source.append("        return parts[0] + '<MID>'\n")
                else:
                     new_source.append(line)
            
            cell['source'] = new_source
            patched = True
            break

if patched:
    print("Writing changes...")
    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=4, ensure_ascii=False)
    print("Done.")
else:
    print("Target code not found in any cell.")
