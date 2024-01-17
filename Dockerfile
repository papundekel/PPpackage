ARG ARCH_TAG=paru-20231217.0.300
# -----------------------------------------------------------------------------

FROM docker.io/greyltc/archlinux-aur:$ARCH_TAG AS base

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

# -----------------------------------------------------------------------------

FROM base AS libalpm-pp

RUN pacman --noconfirm -S meson

COPY --chown=ab:ab PPpackage-arch/libalpm-pp/ /workdir/libalpm-pp
RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

# -----------------------------------------------------------------------------

FROM base AS fakealpm

RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S gcc
RUN pacman --noconfirm -S ninja

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp

COPY PPpackage-arch/fakealpm/ /workdir/fakealpm
RUN ./fakealpm/build.sh fakealpm/ fakealpm/build/ /usr/local

# -----------------------------------------------------------------------------

FROM base as base-python

RUN pacman --noconfirm -S python

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip

# -----------------------------------------------------------------------------

FROM base-python as base-conan

RUN pacman --noconfirm -S cmake
RUN aur-install conan

# -----------------------------------------------------------------------------

FROM base-python as submanager-notconan

RUN pip install hypercorn

# -----------------------------------------------------------------------------

FROM submanager-notconan as submanager-arch

RUN pacman --noconfirm -S pacutils
RUN pacman --noconfirm -S pacman-contrib
RUN pacman --noconfirm -S fakeroot
RUN pacman --noconfirm -S podman

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp
COPY --from=fakealpm /usr/local/lib/libfakealpm.so /usr/local/lib/libfakealpm.so

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-arch/PPpackage_arch/ /workdir/PPpackage-arch/PPpackage_arch
COPY PPpackage-arch/setup.py /workdir/PPpackage-arch/setup.py
RUN pip install PPpackage-arch/

ENTRYPOINT [ "hypercorn", "PPpackage_submanager.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-conan as submanager-conan

RUN pip install hypercorn

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-conan/ /workdir/PPpackage-conan/
RUN pip install PPpackage-conan/

ENTRYPOINT [ "hypercorn", "PPpackage_submanager.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM submanager-notconan as submanager-PP

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-PP/ /workdir/PPpackage-PP
RUN pip install PPpackage-PP/

ENTRYPOINT [ "hypercorn", "PPpackage_submanager.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-conan AS metamanager

ARG USER=root

RUN pacman --noconfirm -S pacutils
RUN pacman --noconfirm -S pacman-contrib
RUN pacman --noconfirm -S fakeroot
RUN pacman --noconfirm -S podman

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp
COPY --from=fakealpm /usr/local/lib/libfakealpm.so /usr/local/lib/libfakealpm.so

RUN mkdir -p /mnt/cache/arch/ && chown $USER /mnt/cache/arch/
RUN mkdir -p /mnt/cache/conan/ && chown $USER /mnt/cache/conan/
RUN mkdir -p /mnt/cache/PP/ && chown $USER /mnt/cache/PP/

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-arch/PPpackage_arch/ /workdir/PPpackage-arch/PPpackage_arch
COPY PPpackage-arch/setup.py /workdir/PPpackage-arch/setup.py
RUN pip install PPpackage-arch/

COPY PPpackage-conan/ /workdir/PPpackage-conan
RUN pip install PPpackage-conan/

COPY PPpackage-PP/ /workdir/PPpackage-PP
RUN pip install PPpackage-PP/

COPY PPpackage/ /workdir/PPpackage
RUN pip install PPpackage/

ENTRYPOINT [ "python", "-m", "PPpackage" ]
