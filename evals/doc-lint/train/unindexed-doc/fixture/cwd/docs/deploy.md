# Deploy

1. Build the image: `docker build -t relay .`
2. Roll it out one instance at a time. Each instance drains for 30 seconds before it stops.
