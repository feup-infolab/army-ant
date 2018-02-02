FROM debian:stretch

ENV user army-ant

# Replace shell with bash so we can source files for nvm
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Install system dependencies
RUN echo deb http://deb.debian.org/debian/ jessie-backports main >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get -y install git curl gcc make zlib1g-dev libbz2-dev libreadline-dev \
  libssl-dev build-essential libsqlite3-dev openjdk-8-jre gnupg libssl1.0.0
COPY ./config/docker/etc/apt/sources.list.d/mongodb-org-3.4.list /etc/apt/sources.list.d
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
RUN apt-get update
RUN apt-get -y install mongodb-org=3.4.10
RUN apt-get -y autoclean

# Prepare working directory
RUN useradd -m ${user}
ENV HOME /home/${user}
WORKDIR $HOME

# Install nvm, node and dependencies
COPY package.json $HOME
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 4.4.7
RUN curl --silent -o- https://raw.githubusercontent.com/creationix/nvm/v0.31.4/install.sh | bash
RUN source $NVM_DIR/nvm.sh \
      && nvm install $NODE_VERSION \
      && nvm alias default $NODE_VERSION \
      && nvm use default
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH
RUN npm install

# Install python and dependencies
COPY .python-version $HOME
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
RUN git clone git://github.com/yyuu/pyenv.git .pyenv
RUN pyenv install
RUN pyenv rehash
COPY requirements.txt $HOME
RUN pip install -r requirements.txt

# Preload MongoDB with collection metadata
ENV mongo_cmd mongod --fork --config /etc/mongod.conf
ENV mongo_dump mongodb-dump-inex_3t_nl
COPY config/docker/${mongo_dump} $HOME/${mongo_dump}
RUN rm -rf $HOME/${mongo_dump}/.gitkeep
RUN ${mongo_cmd} && mongorestore ${mongo_dump} && sync

# Copy remaining files
COPY . $HOME
COPY config/docker/config.yaml $HOME
COPY config/docker/opt/army-ant /opt/army-ant
RUN rm -rf config

# Start server
CMD ${mongo_cmd} && python -u army-ant.py server --host=0.0.0.0 --port=8080

EXPOSE 8080
