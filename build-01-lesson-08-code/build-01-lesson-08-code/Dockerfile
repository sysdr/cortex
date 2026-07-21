# Cortex — Build 01, Lesson 07
# A single-stage image is the right call at this size — Cortex has one
# Python service and no compiled dependencies yet. Multi-stage builds earn
# their complexity later, once there's something worth trimming out of the
# final image (a compiler toolchain, a build-only dependency); adding that
# split today would be solving a problem this lesson doesn't have yet.

FROM python:3.12-slim

WORKDIR /app

# Copying only requirements.txt first, and installing before the rest of
# the code is copied in, means Docker's layer cache can skip the (slow)
# pip install step on every rebuild where only application code changed —
# not requirements.txt itself.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lesson_code.py schema.sql ./

EXPOSE 8000

CMD ["uvicorn", "lesson_code:app", "--host", "0.0.0.0", "--port", "8000"]
