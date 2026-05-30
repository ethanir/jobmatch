"""
Onboarding: turn an uploaded resume into a structured profile.

Flow:
    file (pdf / docx / txt)  ->  extract_text()  ->  parse_resume() [LLM]  ->  profile JSON

Text extraction degrades gracefully by file type and missing libraries, and the
LLM step is the same strict, no-fabrication prompt from prompts.py. Without an
ANTHROPIC_API_KEY, parse_resume() returns an empty schema so the caller can fall
back to manual entry rather than crash.

Deps (optional, only needed for those file types):
    pip install pypdf python-docx
"""
import json
import os

from prompts import RESUME_TO_PROFILE, PROFILE_SCHEMA

# Which model parses resumes. Defaults to the model that has handled this well so
# far; set the RESUME_MODEL env var to point it elsewhere (e.g. a cheaper model)
# WITHOUT a code change. Verify extraction quality before switching it.
RESUME_MODEL = os.environ.get("RESUME_MODEL", "claude-sonnet-4-6")


def extract_text(path):
    """Return plain text from a resume file. Supports .pdf, .docx, .txt/.md."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _from_pdf(path)
    if ext == ".docx":
        return _from_docx(path)
    if ext in (".txt", ".md"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    raise ValueError(f"unsupported resume type: {ext} (use pdf, docx, txt, or md)")


def _from_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pip install pypdf to parse PDF resumes") from e
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def _from_docx(path):
    try:
        import docx
    except ImportError as e:
        raise RuntimeError("pip install python-docx to parse DOCX resumes") from e
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs).strip()


def _empty_profile():
    return json.loads(PROFILE_SCHEMA)


def parse_resume(resume_text, client=None):
    """resume_text -> profile dict via the LLM. Returns empty schema if no LLM available."""
    if not resume_text.strip():
        return _empty_profile()

    if client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            print("  [no ANTHROPIC_API_KEY] returning empty profile for manual entry.")
            return _empty_profile()
        import anthropic
        client = anthropic.Anthropic(api_key=key)

    prompt = RESUME_TO_PROFILE.format(schema=PROFILE_SCHEMA, resume_text=resume_text[:12000])
    msg = client.messages.create(
        model=RESUME_MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("  ! could not parse LLM output; returning empty profile.")
        return _empty_profile()


def parse_resume_pdf(path, client=None):
    """Parse a PDF resume by sending the file itself to the model. This handles
    image-only / scanned PDFs that have no extractable text layer (pypdf returns
    nothing for those), since the model can read the document directly. Degrades
    to an empty schema if there is no API key or the call fails."""
    if client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            print("  [no ANTHROPIC_API_KEY] returning empty profile for manual entry.")
            return _empty_profile()
        import anthropic
        client = anthropic.Anthropic(api_key=key)

    import base64
    try:
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode()
        prompt = RESUME_TO_PROFILE.format(schema=PROFILE_SCHEMA, resume_text="(read the attached PDF)")
        msg = client.messages.create(
            model=RESUME_MODEL, max_tokens=1500,
            messages=[{"role": "user", "content": [
                {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
                {"type": "text", "text": prompt},
            ]}],
        )
    except Exception as e:
        print(f"  ! PDF read failed ({e}); returning empty profile.")
        return _empty_profile()
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("  ! could not parse LLM output; returning empty profile.")
        return _empty_profile()


def onboard(path, out_path="my_profile.json"):
    """Full path: file -> profile JSON saved to disk. Returns the profile dict.
    If a PDF has no extractable text (e.g. a scanned/image-only export), fall back
    to letting the model read the PDF directly rather than returning a blank form."""
    text = extract_text(path)
    if len(text.strip()) >= 40:
        profile = parse_resume(text)
    elif os.path.splitext(path)[1].lower() == ".pdf":
        print("  PDF has no extractable text; reading it directly.")
        profile = parse_resume_pdf(path)
    else:
        profile = _empty_profile()
    with open(out_path, "w") as f:
        json.dump(profile, f, indent=2)
    name = profile.get("name") or "(name not extracted)"
    print(f"  profile for {name} -> {out_path}")
    return profile


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python onboard.py <resume.pdf|.docx|.txt> [out.json]")
        sys.exit(1)
    onboard(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "my_profile.json")
