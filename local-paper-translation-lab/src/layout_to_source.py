from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from src.paper_paths import layout_clean_md_path, layout_regions_jsonl_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import layout_clean_md_path, layout_regions_jsonl_path

DEFAULT_INPUT = Path("outputs/work/layout_regions.jsonl")
DEFAULT_OUTPUT = Path("outputs/work/source_layout_clean.md")


def load_regions(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def normalize_text(text: str) -> str:
    text = text.replace('\r\n','\n').replace('\r','\n')
    text = re.sub(r'-\n(?=[a-z])', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def heading_level(text: str) -> int | None:
    s = text.strip()
    if s == 'Abstract' or s == 'References':
        return 2
    if re.match(r'^\d+\s+\S', s):
        return 2
    if re.match(r'^\d+\.\d+\s+\S', s):
        return 3
    if re.match(r'^[A-Z]\s+\S', s):
        return 2
    return None


def region_sort_key(r):
    bbox = r.get('bbox') or [0,0,0,0]
    x0,y0,x1,y1 = bbox
    return (int(r.get('page_index',0)), float(y0), float(x0))


def render(regions):
    blocks=[]
    for r in sorted(regions, key=region_sort_key):
        role = r.get('layout_role','unknown')
        text = normalize_text(str(r.get('source_hint') or ''))
        if not text:
            continue
        if role == 'noise':
            continue
        if role == 'title':
            level = heading_level(text)
            if level is None:
                blocks.append(text)
            else:
                blocks.append('#'*level + ' ' + text)
            continue
        if role == 'caption':
            if text.startswith('Figure '):
                blocks.append(text)
            elif text.startswith('Table '):
                blocks.append(text)
            else:
                blocks.append(text)
            continue
        if role in {'body','table','figure','equation','unknown'}:
            blocks.append(text)
    return '\n\n'.join(blocks).strip() + '\n'


def run(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    regions = load_regions(input_path)
    md = render(regions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding='utf-8')
    return output_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Render layout regions into a clean markdown-like source artifact.')
    p.add_argument('input_jsonl', nargs='?', default=str(DEFAULT_INPUT))
    p.add_argument('output_md', nargs='?', default=str(DEFAULT_OUTPUT))
    p.add_argument('--paper-id', default=None, help='Optional paper id used to derive default input/output paths')
    p.add_argument('--outputs-dir', default='outputs', help='Base outputs directory used with --paper-id')
    return p


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_jsonl)
    output_path = Path(args.output_md)
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if args.input_jsonl == str(DEFAULT_INPUT):
            input_path = layout_regions_jsonl_path(args.paper_id, outputs_dir)
        if args.output_md == str(DEFAULT_OUTPUT):
            output_path = layout_clean_md_path(args.paper_id, outputs_dir)
    out = run(input_path, output_path)
    print(out)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
