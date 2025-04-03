FROM python:3.10

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8501

EXPOSE $PORT

CMD ["sh", "-c", "streamlit run cotizaciones_app.py --server.port=$PORT --server.enableCORS=false"]