FROM python:3.15-slim

ARG _USER="lilchz"
ARG _UID="1001"
ARG _GID="100"
ARG _SHELL="/bin/bash"

ARG VCS_URL="https://github.com/wayfair-incubator/bigquery-buildkite-plugin"

ARG BUILD_DATE

RUN useradd -m -s "${_SHELL}" -N -u "${_UID}" "${_USER}"

ENV USER ${_USER}
ENV UID ${_UID}
ENV GID ${_GID}
ENV HOME /home/${_USER}
ENV PATH "${HOME}/.local/bin/:${PATH}"
ENV UV_NO_CACHE "true"
# Outside /app so the bind mount of the repository does not hide the environment
ENV UV_PROJECT_ENVIRONMENT "/opt/venv"
ENV PATH "/opt/venv/bin:${PATH}"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.13.10@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f /uv /usr/local/bin/uv

RUN mkdir /app && chown ${UID}:${GID} /app

COPY --chown=${UID}:${GID} ./pyproject.toml ./uv.lock /app/
WORKDIR /app

# Install the locked dependencies (including dev tools) as root, then switch to user
RUN uv sync --locked --no-install-project

USER ${_USER}

CMD bash
