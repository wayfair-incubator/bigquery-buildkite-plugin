FROM python:3.9.6-buster

ARG _USER="lilchz"
ARG _UID="1001"
ARG _GID="100"
ARG _SHELL="/bin/bash"

ARG VERSION=${PLUGIN_REL_VERSION}
ARG DESCRIPTION="Run sonar-scanner in Docker"
ARG VCS_URL="https://github.com/wayfair-incubator/bigquery-buildkite-plugin"

ARG BUILD_DATE
LABEL \
    com.wayfair.name="wayfair-incubator/bigquery-buildkite-plugin" \
    com.wayfair.build-date=${BUILD_DATE} \
    com.wayfair.description=${DESCRIPTION} \
    com.wayfair.vsc_url=${VCS_URL} \
    com.wayfair.maintainer="Jash Parekh <jparekh1@wayfair.com>" \
    com.wayfair.vendor="Wayfair LLC." \
    com.wayfair.version=${VERSION}

RUN useradd -m -s "${_SHELL}" -N -u "${_UID}" "${_USER}"

ENV USER ${_USER}
ENV UID ${_UID}
ENV GID ${_GID}
ENV HOME /home/${_USER}
ENV PATH "${HOME}/.local/bin/:${PATH}"
ENV PIP_NO_CACHE_DIR "true"


RUN mkdir /app && chown ${UID}:${GID} /app

USER ${_USER}

COPY --chown=${UID}:${GID} ./requirements* /app/
WORKDIR /app

RUN pip install -r requirements.lock

CMD bash