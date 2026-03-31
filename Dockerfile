ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python 3 and 7zip for archive extraction
RUN apk add --no-cache python3 p7zip

# Copy files
COPY run.sh /
COPY server.py /
COPY web/ /web/

RUN chmod a+x /run.sh

ENTRYPOINT []
CMD [ "/run.sh" ]
