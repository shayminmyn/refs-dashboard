FROM python:3.12-slim

WORKDIR /app

# Cài dependencies — không dùng layer pip cache cũ khi đổi phiên bản motor/pymongo
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import motor.motor_asyncio; from pymongo import __version__ as pv; print('motor+pymongo OK', pv)"

COPY . .

EXPOSE 4000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
