FROM nginx:alpine

EXPOSE 80

RUN mkdir /app
RUN apk update && apk upgrade && apk add bash

# Copy the build directory contents into the container at /app
ADD ./build /app

COPY nginx.conf /etc/nginx/nginx.conf

CMD nginx -g 'daemon off;'
