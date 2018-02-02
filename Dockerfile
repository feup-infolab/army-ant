FROM alpine

ENV user army-ant
ENV host 0.0.0.0
ENV port 8080

# Install system dependencies
#RUN echo deb http://deb.debian.org/debian/ jessie-backports main >> /etc/apt/sources.list
#RUN apt-get update
#RUN apt-get -y install git curl gcc make zlib1g-dev libbz2-dev libreadline-dev \
  #libssl-dev build-essential libsqlite3-dev openjdk-8-jre gnupg libssl1.0.0
#RUN apt-get -y autoclean

#RUN apk add --no-cache -U curl bash ca-certificates openssl ncurses coreutils python2 make gcc g++ libgcc linux-headers grep util-linux binutils findutils
#RUN apk add --no-cache -U curl bash
RUN apk add --no-cache -U nodejs-npm git python3 libxml2 libxslt openblas openjdk8-jre
RUN apk add --no-cache --virtual .build-deps gcc g++ python3-dev musl-dev postgresql-dev libxml2-dev libxslt-dev openblas-dev

# Replace shell with bash so we can source files for nvm
#RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Prepare working directory
#RUN useradd -m ${user}
#ENV HOME /home/${user}
#WORKDIR $HOME
#ENV HOME /root
#WORKDIR $HOME
#RUN touch .bashrc

# Install nvm, node and dependencies
COPY package.json .
#ENV NVM_DIR /usr/local/nvm
#ENV NODE_VERSION 8.9.4
#RUN curl --silent -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.8/install.sh | bash
#RUN source $NVM_DIR/nvm.sh \
      #&& nvm install -s $NODE_VERSION \
      #&& nvm alias default $NODE_VERSION \
      #&& nvm use default
#ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
#ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH
RUN npm install && npm cache clean --force

# Install python and dependencies
#COPY .python-version .
#ENV PYENV_ROOT .pyenv
#ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
#RUN git clone git://github.com/yyuu/pyenv.git .pyenv
#RUN pyenv install -v
#RUN pyenv rehash
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# TODO Move to beginning
RUN apk add --no-cache -U libpq

# Remove build dependencies
RUN apk --purge del .build-deps

# Link the right files to the right places
RUN ln -s /usr/bin/python3 /usr/local/bin/python
ENV LD_LIBRARY_PATH /usr/lib/jvm/java-1.8-openjdk/jre/lib/amd64/server

# Copy remaining files
COPY . .
COPY config/docker/config.yaml .
COPY config/docker/opt/army-ant /opt/army-ant
RUN rm -rf config

# Start server
CMD python -u army-ant.py server --host=${host} --port=${port}

EXPOSE 8080
