ARG AUR_TAG=paru-20240324.0.314
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

FROM base as base-python

RUN pacman --noconfirm -S python

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip

# -----------------------------------------------------------------------------

FROM base-python AS metamanager

ARG USER=root

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp
COPY --from=fakealpm /usr/local/lib/libfakealpm.so /usr/local/lib/libfakealpm.so

COPY utils/ /workdir/utils
RUN pip install utils/

COPY repository-driver/interface/ /workdir/repository-driver/interface
RUN pip install repository-driver/interface/

COPY metamanager/ /workdir/metamanager
RUN pip install metamanager/

ENTRYPOINT [ "python", "-m", "PPpackage.metamanager" ]
