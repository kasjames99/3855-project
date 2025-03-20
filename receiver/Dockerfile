FROM python:3.9-slim
LABEL maintainer="student@bcit.ca"
RUN mkdir /app
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY . /app
RUN chown -R nobody:nogroup /app
USER nobody
EXPOSE 8081
ENTRYPOINT ["python3"]
CMD ["app.py"]