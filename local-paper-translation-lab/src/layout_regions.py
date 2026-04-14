from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz
import numpy as np
from pdf2zh.doclayout import OnnxModel

try:
    from src.paper_paths import DEFAULT_SAMPLE_PAPER_ID, default_input_pdf, layout_regions_jsonl_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import DEFAULT_SAMPLE_PAPER_ID, default_input_pdf, layout_regions_jsonl_path

DEFAULT_INPUT = default_input_pdf()
DEFAULT_OUTPUT = Path("outputs/work/layout_regions.jsonl")

LABEL_MAP = {
    "plain text": "body",
    "title": "title",
    "figure": "figure",
    "table": "table",
    "isolate_formula": "equation",
    "formula_caption": "caption",
    "figure_caption": "caption",
    "table_caption": "caption",
    "abandon": "noise",
}


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def detect_page_regions(page, model: OnnxModel):
    pix = page.get_pixmap()
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    result = model.predict(img, imgsz=max(32, int(pix.height / 32) * 32))[0]
    detections = []
    for i, box in enumerate(result.boxes):
        cls = int(box.cls)
        label = result.names[cls]
        x0, y0, x1, y1 = [float(v) for v in box.xyxy]
        detections.append(
            {
                "det_id": i,
                "label": label,
                "role": LABEL_MAP.get(label, "unknown"),
                "confidence": float(box.conf),
                "bbox": [x0, y0, x1, y1],
            }
        )
    return detections


def assign_text_blocks(page, detections):
    blocks = []
    for idx, block in enumerate(page.get_text("blocks")):
        x0, y0, x1, y1, text, block_no, block_type = block[:7]
        text = (text or "").strip()
        if not text:
            continue
        bbox = (float(x0), float(y0), float(x1), float(y1))
        best = None
        best_iou = 0.0
        for det in detections:
            iou = bbox_iou(bbox, tuple(det["bbox"]))
            if iou > best_iou:
                best_iou = iou
                best = det
        assigned_label = "unassigned"
        assigned_role = "unknown"
        assigned_conf = 0.0
        if best is not None:
            assigned_label = str(best["label"])
            assigned_role = str(best["role"])
            assigned_conf = float(best["confidence"])
        blocks.append(
            {
                "region_id": f"p{page.number+1:03d}_r{idx:03d}",
                "page_index": page.number,
                "source_hint": text,
                "bbox": [bbox[0], bbox[1], bbox[2], bbox[3]],
                "layout_label": assigned_label,
                "layout_role": assigned_role,
                "confidence": assigned_conf,
                "overlap": best_iou,
                "block_type": int(block_type),
            }
        )
    return blocks


def run(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    model = OnnxModel.from_pretrained()
    doc = fitz.open(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for page in doc:
            detections = detect_page_regions(page, model)
            blocks = assign_text_blocks(page, detections)
            for record in blocks:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate layout-aware region hints using PDFMathTranslate's layout model.")
    parser.add_argument("input_pdf", nargs="?", default=str(DEFAULT_INPUT))
    parser.add_argument("output_jsonl", nargs="?", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive the default output path")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_pdf = Path(args.input_pdf)
    output_jsonl = Path(args.output_jsonl)
    if args.paper_id and args.output_jsonl == str(DEFAULT_OUTPUT):
        output_jsonl = layout_regions_jsonl_path(args.paper_id, Path(args.outputs_dir))
    elif args.output_jsonl == str(DEFAULT_OUTPUT) and args.input_pdf != str(DEFAULT_INPUT):
        output_jsonl = layout_regions_jsonl_path(input_pdf.stem, Path(args.outputs_dir))
    out = run(input_pdf, output_jsonl)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
