FROM python:3.9

WORKDIR /server
ADD . /server/

RUN mkdir /server/files && python -m pip install --upgrade pip \ 
    && pip install -r /server/requirements.txt

CMD ["python", "/server/service/server.py"]

EXPOSE 8080