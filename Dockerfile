ARG AUR_TAG=paru-20240505.0.320
# -----------------------------------------------------------------------------

FROM docker.io/greyltc/archlinux-aur:$AUR_TAG AS base

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

COPY installer/pacman/fakealpm/ /workdir/fakealpm
RUN ./fakealpm/build.sh fakealpm/ fakealpm/build/ /usr/local

# -----------------------------------------------------------------------------

FROM base AS base-python

RUN pacman --noconfirm -S python

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-pacman

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/server/ /workdir/repository-driver/server
RUN pip install repository-driver/server/

COPY repository-driver/pacman/ /workdir/repository-driver/pacman
RUN pip install repository-driver/pacman/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-aur

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/server/ /workdir/repository-driver/server
RUN pip install repository-driver/server/

COPY repository-driver/AUR/ /workdir/repository-driver/AUR
RUN pip install repository-driver/AUR/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-conan

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/server/ /workdir/repository-driver/server
RUN pip install repository-driver/server/

COPY repository-driver/conan/ /workdir/repository-driver/conan
RUN pip install repository-driver/conan/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-pp

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/server/ /workdir/repository-driver/server
RUN pip install repository-driver/server/

COPY repository-driver/PP/ /workdir/repository-driver/PP
RUN pip install repository-driver/PP/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS updater

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/update/ /workdir/repository-driver/update
RUN pip install repository-driver/update/



COPY repository-driver/pacman/ /workdir/repository-driver/pacman
RUN pip install repository-driver/pacman/

COPY repository-driver/AUR/ /workdir/repository-driver/AUR
RUN pip install repository-driver/AUR/

COPY repository-driver/conan/ /workdir/repository-driver/conan
RUN pip install repository-driver/conan/

COPY repository-driver/PP/ /workdir/repository-driver/PP
RUN pip install repository-driver/PP/



ENTRYPOINT [ "python", "-m", "PPpackage.repository_driver.update" ]

# -----------------------------------------------------------------------------

FROM base AS solver

RUN pacman --noconfirm -S jdk-openjdk
RUN pacman --noconfirm -S curl
RUN pacman --noconfirm -S unzip



COPY solver/ /workdir/solver

RUN curl https://release.ow2.org/sat4j/sat4j-core-v20201214.zip -o /workdir/sat4j.zip

RUN unzip /workdir/sat4j.zip -d /workdir/sat4j

RUN javac -classpath /workdir/sat4j/org.sat4j.core.jar /workdir/solver/Solver.java



ENTRYPOINT java -classpath /workdir/sat4j/org.sat4j.core.jar /workdir/solver/Solver.java /mnt/formula /mnt/assumptions > /mnt/output

# -----------------------------------------------------------------------------

FROM base-python AS metamanager

ARG USER=root

COPY --from=fakealpm /usr/local/bin/fakealpm /usr/local/bin/fakealpm
COPY --from=fakealpm /usr/local/bin/fakealpm-executable /usr/local/bin/fakealpm-executable

COPY utils/ /workdir/utils
RUN pip install utils/

COPY container-utils/ /workdir/container-utils
RUN pip install container-utils/



COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/pacman/ /workdir/repository-driver/pacman
RUN pip install repository-driver/pacman/

COPY repository-driver/AUR/ /workdir/repository-driver/AUR
RUN pip install repository-driver/AUR/

COPY repository-driver/conan/ /workdir/repository-driver/conan
RUN pip install repository-driver/conan/

COPY repository-driver/PP/ /workdir/repository-driver/PP
RUN pip install repository-driver/PP/



COPY translator/interface/ /workdir/translator/interface
RUN pip install translator/interface/

COPY translator/pacman/ /workdir/translator/pacman
RUN pip install translator/pacman/

COPY translator/conan/ /workdir/translator/conan
RUN pip install translator/conan/

COPY translator/PP/ /workdir/translator/PP
RUN pip install translator/PP/



COPY installer/interface/ /workdir/installer/interface
RUN pip install installer/interface/

COPY installer/pacman/ /workdir/installer/pacman
RUN pip install installer/pacman/

COPY installer/conan/ /workdir/installer/conan
RUN pip install installer/conan/

COPY installer/simple/ /workdir/installer/simple
RUN pip install installer/simple/



COPY metamanager/ /workdir/metamanager
RUN pip install metamanager/

ENTRYPOINT [ "python", "-m", "PPpackage.metamanager" ]
