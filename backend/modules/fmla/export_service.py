from datetime import datetime
from typing import Any, Dict


DISCLAIMER = (
    "Generated draft only. A qualified staff member must review, edit, and approve this "
    "document before it is shared. Do not auto-submit."
)


def _escape_pdf_text(value: Any, limit: int = 140) -> str:
    text = str(value or "")
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:limit]


def generate_employer_safe_packet(case_record: Dict[str, Any], custom_instructions: str = "") -> Dict[str, str]:
    subject_type = (case_record.get("case_subject_type") or "client").strip().lower()
    subject_label = "employee"
    leave_type = (case_record.get("leave_type") or "continuous").strip().lower()
    request_type = (case_record.get("fmla_request_type") or "new request").strip()
    start_date = case_record.get("leave_start_date") or "to be determined"
    end_date = case_record.get("leave_end_date") or "to be determined"
    expected_return = case_record.get("expected_return_date") or "to be determined"
    employer_name = case_record.get("employer_name") or "Employer"
    review_notes = custom_instructions.strip()

    intro = (
        f"This draft packet supports a request for Family and Medical Leave for the {subject_label}. "
        "It is intentionally limited to the minimum necessary information."
    )
    privacy = (
        "Detailed diagnosis, mental health, and substance use disorder information is intentionally omitted "
        "unless a specific, valid authorization permits disclosure. Any further disclosure should be reviewed "
        "for HIPAA and 42 CFR Part 2 compliance before release."
    )
    body = (
        f"The {subject_label} is requesting {leave_type} leave related to a health condition requiring protected leave. "
        f"The requested leave period begins on {start_date} and is currently expected to end on {end_date}. "
        f"The anticipated return-to-work date is {expected_return}. "
        f"This draft is prepared for {employer_name} and should be reviewed for factual accuracy before export."
    )
    intermittent = ""
    if leave_type == "intermittent":
        intermittent = (
            "The leave may occur in episodic increments. Only schedule and functional limitation details that are "
            "strictly necessary for leave administration should be disclosed."
        )

    additional = ""
    if subject_type == "staff":
        additional = (
            "This record is maintained as a staff HR leave case and must remain segregated from client clinical records."
        )

    instructions = f"Reviewer notes: {review_notes}" if review_notes else ""
    title = "Employer Safe FMLA Packet Draft"
    content = "\n\n".join(part for part in [DISCLAIMER, intro, privacy, body, intermittent, additional, instructions] if part)
    return {
        "draft_title": title,
        "draft_content": content,
        "warning_text": DISCLAIMER,
    }


def build_packet_pdf(title: str, content: str) -> bytes:
    lines = [title, "", DISCLAIMER, ""]
    lines.extend((content or "").splitlines() or ["No content provided."])

    y = 760
    stream_lines = ["BT", "/F2 16 Tf", f"40 {y} Td"]
    first = True
    for raw_line in lines[:40]:
        line = _escape_pdf_text(raw_line)
        if not first:
            stream_lines.append("0 -18 Td")
        font = "/F2 11 Tf" if raw_line == DISCLAIMER or raw_line.isupper() else "/F1 10 Tf"
        if first:
            font = "/F2 16 Tf"
            first = False
        stream_lines.append(font)
        stream_lines.append(f"({line}) Tj")
    stream_lines.append("0 -20 Td")
    stream_lines.append("/F1 9 Tf")
    stream_lines.append(f"(Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines) + "\n"
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
        f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("ascii"))
    return bytes(pdf)
