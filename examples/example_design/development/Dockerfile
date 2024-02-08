ARG NAUTOBOT_VERSION
ARG PYTHON_VER

FROM ghcr.io/nautobot/nautobot-dev:${NAUTOBOT_VERSION}-py${PYTHON_VER}

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./poetry.lock /source/

# Install the nautobot project to include Nautobot
RUN cd /source && \
    poetry install --no-interaction --no-ansi && \
    mkdir /tmp/dist && \
    poetry export --without-hashes -o /tmp/dist/requirements.txt


COPY development/nautobot_config.py /opt/nautobot/nautobot_config.py

WORKDIR /source

