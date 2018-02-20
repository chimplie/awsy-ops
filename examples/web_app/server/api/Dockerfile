FROM python:3.6

EXPOSE 5000

# Install system-wide dependencies
RUN apt-get update

# Install Python requirements
ADD ./requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

# Set the working directory to /app
RUN mkdir /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Entry point
CMD /app/app.py
