FROM python:3.9-slim
LABEL maintainer="kjames39@bcit.ca"

# Install required packages for mysqlclient
RUN apt-get update && apt-get install -y default-libmysqlclient-dev build-essential pkg-config

RUN mkdir /app

# Copy requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

# Set the working directory
WORKDIR /app

# Install dependencies
RUN pip3 install -r requirements.txt

# Copy the source code
COPY . /app

# Change permissions and become a non-privileged user
RUN chown -R nobody:nogroup /app
USER nobody

# Tells on which port the service listens in the container
EXPOSE 8090

# Entrypoint = run Python
ENTRYPOINT ["python3"]

# Default = run app.py
CMD ["app.py"]