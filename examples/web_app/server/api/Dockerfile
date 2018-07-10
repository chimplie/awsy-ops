FROM python:3.6

EXPOSE 5000

# Install system-wide dependencies
RUN apt-get update
RUN apt-get -y install curl

# Install Python requirements
ADD ./requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

# Install AWS environment tools
RUN curl -L -o /bin/aws-env https://github.com/Droplr/aws-env/raw/872ca7e45a8fdc519ff40745c56175ae81d3b66b/bin/aws-env-linux-amd64
RUN chmod +x /bin/aws-env

# Set the working directory to /app
RUN mkdir /app
WORKDIR /app

# Make all files in ./bin executable
RUN chmod +x /app/bin/*

# Set the default command
CMD bash -c "bin/run.sh"
