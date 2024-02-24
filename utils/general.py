import json
import re


def sanitize_for_latex(s: str) -> str:
    return s.strip().replace("$", "").replace("%", " percent").replace("&", " and ")
    """Sanitizes a string so that it can be properly compiled in TeX.
    Escapes the most common TeX special characters: ~^_#%${}
    Removes backslashes.
    """
    s = re.sub('\\\\', '', s)
    s = re.sub(r'([_^$%&#{}])', r'\\\1', s)
    s = re.sub(r'\~', r'\\~{}', s)
    return s


def parse_json_garbage(s: str):
    s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return json.loads(s[:e.pos])


def load_string(fp: str) -> str:
    with open(fp, 'r') as f:
        job = f.read().strip()

    return job


def load_prompt_string(file_path: str):
    with open(file_path, 'r') as f:
        data = f.read()

    return data
