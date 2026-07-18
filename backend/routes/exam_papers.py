# ============================================================
# routes/exam_papers.py — /api/exam-papers/upload endpoint
# Lets a student/teacher upload a past exam paper PDF so its
# questions can be flagged as "important" in future chat answers.
# ============================================================

from flask import Blueprint, request, jsonify

from services.exam_papers import (
    extract_text_from_pdf,
    split_into_questions,
    add_exam_questions,
    list_exam_papers,
)

exam_papers_bp = Blueprint("exam_papers", __name__)


@exam_papers_bp.route("/exam-papers/list", methods=["GET"])
def get_exam_papers():
    """
    GET /api/exam-papers/list
    Returns a summary of every uploaded past exam paper.
    Response: { "papers": [{ "source", "subject", "standard", "class", "question_count" }, ...] }
    """
    try:
        return jsonify({"papers": list_exam_papers()})
    except Exception as e:
        return jsonify({"error": f"Could not load uploaded papers: {str(e)}"}), 500


@exam_papers_bp.route("/exam-papers/upload", methods=["POST"])
def upload_exam_paper():
    """
    POST /api/exam-papers/upload
    Multipart form-data:
        pdf     : the exam paper PDF file
        subject : maths | science | social
        class   : 8 | 9 | 10
    Returns:
        { "questions_found": N, "questions_added": M }
    """
    pdf_file = request.files.get("pdf")
    if not pdf_file or not pdf_file.filename:
        return jsonify({"error": "No PDF file uploaded. Use the 'pdf' form field."}), 400

    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    subject = (request.form.get("subject") or "").lower().strip()
    if subject not in ("maths", "science", "social"):
        return jsonify({"error": "subject must be one of: maths, science, social"}), 400

    student_class = (request.form.get("class") or "").strip()
    if student_class not in ("8", "9", "10"):
        return jsonify({"error": "class must be one of: 8, 9, 10"}), 400
    standard = f"standard_{student_class}"

    try:
        raw_text = extract_text_from_pdf(pdf_file.stream)
    except Exception as e:
        return jsonify({"error": f"Could not read PDF: {str(e)}"}), 400

    if not raw_text.strip():
        return jsonify({
            "error": "No extractable text found in this PDF.",
            "hint": "Scanned/image-only PDFs aren't supported — try a text-based PDF."
        }), 422

    questions = split_into_questions(raw_text)
    if not questions:
        return jsonify({
            "error": "Could not identify individual questions in this PDF.",
            "hint": "Questions should be numbered, e.g. '1.', '2)', 'Q3.'"
        }), 422

    try:
        added = add_exam_questions(questions, subject=subject, standard=standard, source=pdf_file.filename)
    except Exception as e:
        return jsonify({"error": f"Could not save the extracted questions: {str(e)}"}), 500

    return jsonify({
        "questions_found": len(questions),
        "questions_added": added,
    })
