# Specify a base image
FROM node:20

WORKDIR /app

# Install some dependencies
COPY package.json ./

RUN npm install

COPY . .

EXPOSE 5173

# Command to run the Vue development server
CMD ["npm", "run", "dev", "--", "--host"]