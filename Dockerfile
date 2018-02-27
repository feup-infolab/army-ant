# Let's keep it small with alpine
FROM alpine

# Build configurations
ENV host 0.0.0.0
ENV port 8080

# Install run and compile time dependencies
RUN apk add --no-cache -U nodejs-npm git python3 libpq libxml2 libxslt openblas openjdk8-jre
RUN apk add --no-cache --virtual .build-deps gcc g++ python3-dev musl-dev postgresql-dev libxml2-dev libxslt-dev openblas-dev make

# Create a directory to put stuff
RUN mkdir army-ant
WORKDIR army-ant

# Install node dependencies
COPY package.json .
COPY package-lock.json .
RUN npm install && npm cache clean --force

# Install python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Remove compile time dependencies
RUN apk --purge del .build-deps

# Link the right files to the right places
RUN ln -s /usr/bin/python3 /usr/local/bin/python
ENV LD_LIBRARY_PATH /usr/lib/jvm/java-1.8-openjdk/jre/lib/amd64/server

# Download and install WordNet 3.0
RUN wget http://wordnetcode.princeton.edu/3.0/WNdb-3.0.tar.gz
RUN tar xvzf WNdb-3.0.tar.gz
RUN mv dict /usr/share/wordnet
RUN rm -f WNdb-3.0.tar.gz

# Copy code, configuration and data
COPY . .
COPY config/docker/config.yaml .
COPY config/docker/opt/army-ant /opt/army-ant
RUN rm -rf config

# Start the server
CMD python -u army-ant.py server --host=${host} --port=${port}

# Expose the configured port
EXPOSE ${port}
