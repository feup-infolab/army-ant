# I would use Alpine, if I could compile igraph without glibc...
FROM debian:stretch

SHELL ["/bin/bash", "-c"]

# Build configurations
ENV host 0.0.0.0
ENV port 8080

WORKDIR /root/army-ant

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

# Install miniconda
RUN curl -OL https://repo.anaconda.com/miniconda/Miniconda3-py37_4.8.2-Linux-x86_64.sh
RUN bash Miniconda3-py37_4.8.2-Linux-x86_64.sh -b
RUN rm -f Miniconda3-py37_4.8.2-Linux-x86_64.sh

# Install conda environment and dependencies
COPY environment.yml .
ENV PATH ~/miniconda3/bin:$PATH
RUN conda init bash
RUN conda env create -f environment.yml

# Build java implementation and clean maven dependencies
COPY external/lib/Grph external/lib/Grph
RUN cd external/lib/Grph && mvn install
COPY external/java-impl external/java-impl
RUN cd external/java-impl && mvn compile assembly:single
RUN rm -rf ~/.m2

# Copy code, configuration and data
COPY . .

# Start the server
CMD source ~/.bashrc \
    && conda activate py36-armyant \
    && python -u army-ant.py server --host=${host} --port=${port}

# Expose the configured port
EXPOSE ${port}
