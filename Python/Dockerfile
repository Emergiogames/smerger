# # Use an official Python runtime as a parent image
# FROM python:3.12

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # Set the working directory
# WORKDIR /smerger

# # Install dependencies
# COPY requirements.txt /smerger/
# RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# # Copy the project code into the container
# COPY . /smerger/

# RUN pip install \
#     gunicorn \
#     uvicorn[standard] \
#     httptools \
#     uvloop \
#     websockets \
#     aiohttp \
#     channels-redis

# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "smerger.wsgi:application"]

# Use an official Python runtime as a parent image
FROM python:3.12

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /smerger

# Install dependencies
COPY requirements.txt /smerger/
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy the project code into the container
COPY . /smerger/

RUN pip install \
    gunicorn \
    uvicorn[standard] \
    httptools \
    uvloop \
    websockets \
    aiohttp \
    channels-redis

# Install cron
RUN apt-get update && apt-get install -y cron

# Copy cronjob file
COPY cronjob /etc/cron.d/cronjob

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/cronjob

# Apply cron job
RUN crontab /etc/cron.d/cronjob

RUN touch /var/log/cron.log && chmod 666 /var/log/cron.log

# Start cron and the application
CMD service cron start && gunicorn --bind 0.0.0.0:8000 smerger.wsgi:application