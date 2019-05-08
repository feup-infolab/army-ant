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
#RUN echo deb http://deb.debian.org/debian/ jessie-backports main >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get -y install build-essential gcc make maven curl git openjdk-8-jdk gnupg libssl1.1 wordnet \
    zlib1g-dev libbz2-dev libreadline-dev libssl-dev libsqlite3-dev libxml2-dev libffi-dev

# Install node and dependencies
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get -y install nodejs
COPY package.json .
COPY package-lock.json .
RUN npm install && npm cache clean --force

# Install Python
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
RUN git clone git://github.com/yyuu/pyenv.git $HOME/.pyenv
COPY .python-version .
RUN pyenv install
RUN pyenv rehash
RUN pyenv global $(cat .python-version)

# Install TensorFlow Ranking
RUN curl -L https://github.com/bazelbuild/bazel/releases/download/0.18.1/bazel_0.18.1-linux-x86_64.deb \
    --output /tmp/bazel_0.18.1-linux-x86_64.deb
RUN dpkg -i --force-depends /tmp/bazel_0.18.1-linux-x86_64.deb
RUN apt-get -y install -f
RUN git clone https://github.com/tensorflow/ranking.git /tmp/ranking
RUN cd /tmp/ranking && git checkout 099b17b11e7f699f30bcdea18a4323df7827fde8
RUN cd /tmp/ranking && bazel build //tensorflow_ranking/tools/pip_package:build_pip_package
RUN pip install wheel
RUN cd /tmp/ranking && bazel-bin/tensorflow_ranking/tools/pip_package/build_pip_package /tmp/ranking_pip
RUN pip install /tmp/ranking_pip/tensorflow_ranking*.whl
RUN rm -rf /tmp/bazel* /tmp/ranking*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build java implementation and clean maven dependencies
COPY external/lib/Grph external/lib/Grph
RUN cd external/lib/Grph && mvn install
COPY external/java-impl external/java-impl
RUN cd external/java-impl && mvn compile assembly:single
RUN rm -rf $HOME/.m2

# Copy code, configuration and data
COPY . .
RUN rm -rf config

# Start the server
CMD python -u army-ant.py server --host=${host} --port=${port}

# Expose the configured port
EXPOSE ${port}
