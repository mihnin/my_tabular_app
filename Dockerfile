FROM  --platform=amd64 python:3.10.16-bullseye
RUN apt update -y 
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD [ "streamlit","run", "app.py" ]