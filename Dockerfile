FROM python:3
COPY . /app
WORKDIR /app
RUN apt update && apt install -y git && pip install --upgrade -r requirements.txt
CMD python -u main.py
