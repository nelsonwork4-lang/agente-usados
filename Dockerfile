FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    fonts-liberation libglib2.0-0 libnss3 \
    libfontconfig1 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
    libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
    libxrender1 libxss1 libxtst6 libxkbcommon0 libgbm1 libasound2 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps
# cache-bust: 20260531053546
COPY . .
CMD ["python", "agendador.py"]
