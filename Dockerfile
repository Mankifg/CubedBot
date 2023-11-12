FROM python:3.10
COPY . /app
WORKDIR /app
RUN apt update && apt install -y git 
RUN pip install --upgrade -r requirements.txt
CMD python -u main.py
