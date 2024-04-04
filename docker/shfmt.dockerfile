FROM golang:1.22.2 AS gobuilder

ENV USER=formatter
ENV UID=10001

RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    "${USER}"

RUN GO111MODULE=on go install mvdan.cc/sh/v3/cmd/shfmt@latest

FROM scratch

COPY --from=gobuilder /etc/passwd /etc/passwd
COPY --from=gobuilder /etc/group /etc/group
COPY --from=gobuilder /go/bin/shfmt /go/bin/shfmt

USER formatter:formatter

WORKDIR /plugin

ENTRYPOINT [ "/go/bin/shfmt" ]