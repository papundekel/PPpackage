FROM docker.io/greyltc/archlinux-aur AS base

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

# -----------------------------------------------------------------------------

FROM base AS fakealpm

RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S gcc
RUN pacman --noconfirm -S ninja
RUN pacman --noconfirm -S boost
RUN pacman --noconfirm -S nlohmann-json

COPY src/installer/pacman/fakealpm/ /workdir/fakealpm
RUN ./fakealpm/build.sh fakealpm/ fakealpm/build/ /usr/local

# -----------------------------------------------------------------------------

FROM base AS base-python

RUN pacman --noconfirm -S python

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip

# -----------------------------------------------------------------------------

FROM base-python AS updater

COPY src/utils/async/ /workdir/utils/async
RUN pip install utils/async

COPY src/repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/



COPY src/utils/json /workdir/utils/json
RUN pip install utils/json

COPY src/utils/cli /workdir/utils/cli
RUN pip install utils/cli

COPY src/utils/python /workdir/utils/python
RUN pip install utils/python

COPY src/repository-driver/update/ /workdir/repository-driver/update
RUN pip install repository-driver/update/



COPY src/utils/file/ /workdir/utils/file
RUN pip install utils/file

COPY src/utils/lock/ /workdir/utils/lock
RUN pip install utils/lock

COPY src/repository-driver/pacman/ /workdir/repository-driver/pacman
RUN pip install repository-driver/pacman/



COPY src/repository-driver/AUR/ /workdir/repository-driver/AUR
RUN pip install repository-driver/AUR/



COPY src/repository-driver/conan/ /workdir/repository-driver/conan
RUN pip install repository-driver/conan/



COPY examples/ /usr/share/doc/PPpackage/examples/



ENTRYPOINT [ "python", "-m", "PPpackage.repository_driver.update" ]

# -----------------------------------------------------------------------------

FROM base AS sat4j

RUN pacman --noconfirm -S curl
RUN pacman --noconfirm -S unzip

RUN curl https://release.ow2.org/sat4j/sat4j-core-v20201214.zip -o /workdir/sat4j.zip
RUN unzip /workdir/sat4j.zip -d /workdir/sat4j

# -----------------------------------------------------------------------------

FROM base AS solver

RUN pacman --noconfirm -S jdk-openjdk

COPY --from=sat4j /workdir/sat4j/ /workdir/sat4j

COPY src/solver/ /workdir/solver

RUN javac -classpath /workdir/sat4j/org.sat4j.core.jar /workdir/solver/Solver.java

ENTRYPOINT java -classpath /workdir/sat4j/org.sat4j.core.jar /workdir/solver/Solver.java /mnt/formula /mnt/assumptions > /mnt/output

# -----------------------------------------------------------------------------

FROM base-python AS metamanager

ARG USER=root

COPY --from=fakealpm /usr/local/bin/fakealpm /usr/local/bin/fakealpm
COPY --from=fakealpm /usr/local/bin/fakealpm-executable /usr/local/bin/fakealpm-executable

COPY src/utils/json /workdir/utils/json
RUN pip install utils/json

COPY src/utils/async /workdir/utils/async
RUN pip install utils/async

COPY src/utils/cli /workdir/utils/cli
RUN pip install utils/cli

COPY src/utils/container /workdir/utils/container
RUN pip install utils/container

COPY src/utils/file /workdir/utils/file
RUN pip install utils/file

COPY src/utils/lock /workdir/utils/lock
RUN pip install utils/lock

COPY src/utils/python /workdir/utils/python
RUN pip install utils/python

COPY src/utils/serialization /workdir/utils/serialization
RUN pip install utils/serialization



COPY src/repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY src/repository-driver/pacman/ /workdir/repository-driver/pacman
RUN pip install repository-driver/pacman/

COPY src/repository-driver/AUR/ /workdir/repository-driver/AUR
RUN pip install repository-driver/AUR/

COPY src/repository-driver/conan/ /workdir/repository-driver/conan
RUN pip install repository-driver/conan/



COPY src/translator/interface/ /workdir/translator/interface
RUN pip install translator/interface/

COPY src/translator/pacman/ /workdir/translator/pacman
RUN pip install translator/pacman/

COPY src/translator/conan/ /workdir/translator/conan
RUN pip install translator/conan/



COPY src/installer/interface/ /workdir/installer/interface
RUN pip install installer/interface/

COPY src/installer/pacman/ /workdir/installer/pacman
RUN pip install installer/pacman/

COPY src/installer/conan/ /workdir/installer/conan
RUN pip install installer/conan/



COPY src/generator/interface/ /workdir/generator/interface
RUN pip install generator/interface/

COPY src/generator/conan/ /workdir/generator/conan
RUN pip install generator/conan/



COPY src/metamanager/ /workdir/metamanager
RUN pip install metamanager/

ENTRYPOINT [ "python", "-m", "PPpackage.metamanager" ]
