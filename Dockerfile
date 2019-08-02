FROM python

COPY . .

RUN pip install pycld2 aiohttp pandas geoip2 beautifulsoup4

EXPOSE 8080

CMD ["python", "./server.py"]
