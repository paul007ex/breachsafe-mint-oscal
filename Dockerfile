# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
FROM python:3.12-slim

# OSCAL is a compliance artifact; keep the image reproducible and minimal.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy metadata and source, then install the package (provides the `mint-oscal`
# console script defined in pyproject.toml).
COPY pyproject.toml LICENSE ./
COPY src ./src
RUN pip install .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 mint
USER mint

ENTRYPOINT ["mint-oscal"]
CMD ["--help"]
