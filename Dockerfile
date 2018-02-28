# I would use Alpine, if I could compile igraph without glibc...
FROM debian:stretch

# Build configurations
ENV host 0.0.0.0
ENV port 8080
ENV user army-ant

# Prepare working directory
RUN useradd -m ${user}
ENV HOME /home/${user}
WORKDIR $HOME

# Install system dependencies
RUN echo deb http://deb.debian.org/debian/ jessie-backports main >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get -y install build-essential gcc make maven curl git openjdk-8-jre gnupg libssl1.0.0 wordnet \
    zlib1g-dev libbz2-dev libreadline-dev libssl-dev libsqlite3-dev libxml2-dev

# Install node and dependencies
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get -y install nodejs
COPY package.json .
COPY package-lock.json .
RUN npm install && npm cache clean --force

# Build java implementation and clean maven dependencies
COPY external/java-impl external/java-impl
RUN cd external/java-impl && mvn assembly:single
RUN rm -rf $HOME/.m2

# Install python and dependencies
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
RUN git clone git://github.com/yyuu/pyenv.git $HOME/.pyenv
COPY .python-version .
RUN pyenv install
RUN pyenv rehash
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code, configuration and data
COPY . .
COPY config/docker/config.yaml .
COPY config/docker/opt/army-ant /opt/army-ant
RUN rm -rf config

# Start the server
CMD python -u army-ant.py server --host=${host} --port=${port}

# Expose the configured port
EXPOSE ${port}
