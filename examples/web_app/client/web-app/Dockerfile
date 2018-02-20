FROM nginx:alpine

EXPOSE 8080

RUN mkdir /app
RUN apk update && apk upgrade && apk add bash
# Copy the current directory contents into the container at /app
ADD . /app

COPY nginx.conf /etc/nginx/nginx.conf

CMD nginx -g 'daemon off;'
