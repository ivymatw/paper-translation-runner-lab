from __future__ import annotations

import argparse
import re
import zlib
from pathlib import Path
from typing import Iterator

try:
    from src.paper_paths import DEFAULT_SAMPLE_PAPER_ID, default_input_pdf, extracted_md_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import DEFAULT_SAMPLE_PAPER_ID, default_input_pdf, extracted_md_path

DEFAULT_INPUT = default_input_pdf()
DEFAULT_OUTPUT = Path("outputs/work/source_extracted.md")

STREAM_OBJECT_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.S)


def decode_pdf_literal(data: bytes) -> str:
    out = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte != 0x5C:  # backslash
            out.append(byte)
            i += 1
            continue

        i += 1
        if i >= len(data):
            out.append(0x5C)
            break

        esc = data[i]
        if esc in b"nrtbf":
            out.extend({ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b", ord("f"): b"\f"}[esc])
            i += 1
        elif esc in b"()\\":
            out.append(esc)
            i += 1
        elif esc in b"\n\r":
            if esc == ord("\r") and i + 1 < len(data) and data[i + 1] == ord("\n"):
                i += 2
            else:
                i += 1
        elif 48 <= esc <= 55:
            octal = bytes([esc])
            i += 1
            for _ in range(2):
                if i < len(data) and 48 <= data[i] <= 55:
                    octal += bytes([data[i]])
                    i += 1
                else:
                    break
            out.append(int(octal, 8))
        else:
            out.append(esc)
            i += 1
    return out.decode("latin-1", errors="replace")


class PDFContentTokenizer:
    def __init__(self, data: bytes):
        self.data = data
        self.i = 0
        self.n = len(data)

    def __iter__(self) -> Iterator[object]:
        while True:
            token = self.next_token()
            if token is None:
                return
            yield token

    def next_token(self) -> object | None:
        self._skip_ws_and_comments()
        if self.i >= self.n:
            return None

        ch = self.data[self.i]
        if ch == ord("("):
            return self._parse_literal()
        if ch == ord("["):
            self.i += 1
            arr = []
            while True:
                self._skip_ws_and_comments()
                if self.i >= self.n:
                    break
                if self.data[self.i] == ord("]"):
                    self.i += 1
                    break
                item = self.next_token()
                if item is None:
                    break
                arr.append(item)
            return arr
        if ch == ord("/"):
            self.i += 1
            start = self.i
            while self.i < self.n and self.data[self.i] not in b"()<>[]{}/%" and not chr(self.data[self.i]).isspace():
                self.i += 1
            return "/" + self.data[start:self.i].decode("latin-1", errors="replace")
        if ch == ord("<") and self.i + 1 < self.n and self.data[self.i + 1] != ord("<"):
            return self._parse_hex_string()
        if ch in (ord("<"), ord(">"), ord("{"), ord("}"), ord("]")):
            self.i += 1
            return chr(ch)

        start = self.i
        delimiters = b"()<>[]{}/%"
        while self.i < self.n and self.data[self.i] not in delimiters and not chr(self.data[self.i]).isspace():
            self.i += 1
        token = self.data[start:self.i].decode("latin-1", errors="replace")
        return self._coerce(token)

    def _skip_ws_and_comments(self) -> None:
        while self.i < self.n:
            ch = self.data[self.i]
            if chr(ch).isspace():
                self.i += 1
                continue
            if ch == ord("%"):
                while self.i < self.n and self.data[self.i] not in (ord("\n"), ord("\r")):
                    self.i += 1
                continue
            break

    def _parse_literal(self) -> str:
        assert self.data[self.i] == ord("(")
        self.i += 1
        depth = 1
        out = bytearray()
        while self.i < self.n:
            ch = self.data[self.i]
            if ch == ord("\\"):
                out.append(ch)
                self.i += 1
                if self.i < self.n:
                    out.append(self.data[self.i])
                    self.i += 1
                continue
            if ch == ord("("):
                depth += 1
                out.append(ch)
                self.i += 1
                continue
            if ch == ord(")"):
                depth -= 1
                if depth == 0:
                    self.i += 1
                    break
                out.append(ch)
                self.i += 1
                continue
            out.append(ch)
            self.i += 1
        return decode_pdf_literal(bytes(out))

    def _parse_hex_string(self) -> str:
        self.i += 1
        start = self.i
        while self.i < self.n and self.data[self.i] != ord(">"):
            self.i += 1
        raw = re.sub(rb"\s+", b"", self.data[start:self.i])
        if len(raw) % 2 == 1:
            raw += b"0"
        self.i += 1 if self.i < self.n else 0
        try:
            decoded = bytes.fromhex(raw.decode("ascii"))
        except Exception:
            decoded = raw
        return decoded.decode("latin-1", errors="replace")

    @staticmethod
    def _coerce(token: str) -> object:
        if not token:
            return token
        try:
            if any(c in token for c in ".+-"):
                return float(token)
            return int(token)
        except ValueError:
            return token


def iter_content_streams(pdf_bytes: bytes) -> Iterator[bytes]:
    for match in STREAM_OBJECT_RE.finditer(pdf_bytes):
        obj = match.group(3)
        if b"stream" not in obj:
            continue
        header, rest = obj.split(b"stream", 1)
        stream, _ = rest.split(b"endstream", 1)
        stream = stream.strip(b"\r\n")
        filters = []
        if b"/Filter" in header:
            filter_match = re.search(rb"/Filter\s*(\[[^\]]+\]|/\w+)", header)
            if filter_match:
                raw_filter = filter_match.group(1)
                filters = re.findall(rb"/(\w+)", raw_filter)
        data = stream
        try:
            for pdf_filter in filters:
                if pdf_filter == b"FlateDecode":
                    data = zlib.decompress(data)
                else:
                    data = b""
                    break
        except Exception:
            continue
        if not filters:
            data = stream
        if b"BT" in data and (b"Tj" in data or b"TJ" in data):
            yield data


def extract_text_from_stream(stream_data: bytes) -> str:
    tokens = PDFContentTokenizer(stream_data)
    operands: list[object] = []
    pieces: list[str] = []
    line_open = False

    def add_text(text: str) -> None:
        nonlocal line_open
        cleaned = "".join(ch if ch == "\n" or ch == "\t" or ord(ch) >= 32 else " " for ch in text)
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned.strip():
            return
        if line_open and pieces and not pieces[-1].endswith(("\n", " ")):
            pieces.append(" ")
        pieces.append(cleaned.strip())
        line_open = True

    def add_newline(double: bool = False) -> None:
        nonlocal line_open
        if not pieces:
            return
        if pieces[-1].endswith("\n\n"):
            line_open = False
            return
        if pieces[-1].endswith("\n"):
            if double and not pieces[-1].endswith("\n\n"):
                pieces.append("\n")
            line_open = False
            return
        pieces.append("\n\n" if double else "\n")
        line_open = False

    for token in tokens:
        if isinstance(token, str) and token in {"BT", "ET", "Tj", "TJ", "'", '"', "Td", "TD", "T*", "Tm"}:
            op = token
            if op == "BT":
                add_newline(double=True)
            elif op == "ET":
                add_newline(double=True)
            elif op in {"Td", "TD", "T*", "Tm"}:
                add_newline()
            elif op in {"Tj", "'", '"'}:
                if op in {"'", '"'}:
                    add_newline()
                if operands:
                    last = operands[-1]
                    if isinstance(last, str):
                        add_text(last)
            elif op == "TJ":
                if operands:
                    last = operands[-1]
                    if isinstance(last, list):
                        parts: list[str] = []
                        for item in last:
                            if isinstance(item, str):
                                parts.append(item)
                            elif isinstance(item, (int, float)) and item <= -120:
                                parts.append(" ")
                        add_text("".join(parts))
            operands.clear()
        else:
            operands.append(token)

    text = "".join(pieces)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def extract_text(pdf_path: Path) -> str:
    pdf_bytes = pdf_path.read_bytes()
    chunks = []
    for stream in iter_content_streams(pdf_bytes):
        text = extract_text_from_stream(stream)
        if text:
            chunks.append(text)
    combined = "\n\n".join(chunks)
    combined = re.sub(r"\n{3,}", "\n\n", combined).strip()
    return combined


def format_markdown(pdf_path: Path, extracted_text: str) -> str:
    return (
        f"# Source Extracted Text\n\n"
        f"Source PDF: {pdf_path}\n\n"
        f"## Extracted Content\n\n"
        f"{extracted_text}\n"
    )


def run(pdf_path: Path, output_path: Path) -> Path:
    extracted_text = extract_text(pdf_path)
    if not extracted_text.strip():
        raise RuntimeError(f"No text extracted from {pdf_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_markdown(pdf_path, extracted_text), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract machine-readable text from a PDF into markdown.")
    parser.add_argument("input_pdf", nargs="?", default=str(DEFAULT_INPUT), help="Path to the input PDF")
    parser.add_argument("output_md", nargs="?", default=str(DEFAULT_OUTPUT), help="Path to the output markdown file")
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive the default output path")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    input_pdf = Path(args.input_pdf)
    output_path = Path(args.output_md)
    if args.paper_id and args.output_md == str(DEFAULT_OUTPUT):
        output_path = extracted_md_path(args.paper_id, Path(args.outputs_dir))
    elif args.paper_id and args.output_md != str(DEFAULT_OUTPUT):
        output_path = Path(args.output_md)
    elif args.output_md == str(DEFAULT_OUTPUT) and args.input_pdf != str(DEFAULT_INPUT):
        output_path = extracted_md_path(input_pdf.stem, Path(args.outputs_dir))
    output_path = run(input_pdf, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
