FROM python:3.12

WORKDIR /app
COPY . /app

RUN pip install .
RUN charterloom build

EXPOSE 8000
CMD ["charterloom", "serve", "host=0.0.0.0", "port=8000"]
