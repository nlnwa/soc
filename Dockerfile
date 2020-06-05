FROM python

COPY . /tmp/

WORKDIR /tmp/

RUN pip install -r /tmp/requirements.txt

EXPOSE 8080

CMD ["python", "norvegica/server.py"]
