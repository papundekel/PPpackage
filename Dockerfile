ARG AUR_TAG=paru-20240407.0.316
# -----------------------------------------------------------------------------

FROM docker.io/greyltc/archlinux-aur:$AUR_TAG AS base

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

# -----------------------------------------------------------------------------

FROM base AS libalpm-pp

RUN pacman --noconfirm -S meson

COPY --chown=ab:ab installer/pacman/libalpm-pp/ /workdir/libalpm-pp
RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

# -----------------------------------------------------------------------------

FROM base AS fakealpm

RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S gcc
RUN pacman --noconfirm -S ninja

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp

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

COPY repository-driver/pacman/ /workdir/repository-driver/pacman
RUN pip install repository-driver/pacman/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-AUR

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/AUR/ /workdir/repository-driver/AUR
RUN pip install repository-driver/AUR/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-conan

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/conan/ /workdir/repository-driver/conan
RUN pip install repository-driver/conan/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS repository-driver-PP

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY repository-driver/PP/ /workdir/repository-driver/PP
RUN pip install repository-driver/PP/

ENTRYPOINT [ "hypercorn", "PPpackage.repository_driver.server.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-python AS metamanager

ARG USER=root

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp
COPY --from=fakealpm /usr/local/lib/libfakealpm.so /usr/local/lib/libfakealpm.so

COPY utils/ /workdir/utils
RUN pip install utils/

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

COPY metamanager/ /workdir/metamanager
RUN pip install metamanager/

ENTRYPOINT [ "python", "-m", "PPpackage.metamanager" ]
