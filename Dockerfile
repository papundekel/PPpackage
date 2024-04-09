ARG AUR_TAG=paru-20240324.0.314
# -----------------------------------------------------------------------------

FROM docker.io/greyltc/archlinux-aur:$AUR_TAG AS base

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

# -----------------------------------------------------------------------------

FROM base AS libalpm-pp

RUN pacman --noconfirm -S meson

COPY --chown=ab:ab PPpackage-pacman-utils/libalpm-pp/ /workdir/libalpm-pp
RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

# -----------------------------------------------------------------------------

FROM base AS fakealpm

RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S gcc
RUN pacman --noconfirm -S ninja

COPY --from=libalpm-pp /usr/share/libalpm-pp /usr/share/libalpm-pp

COPY PPpackage-pacman-utils/fakealpm/ /workdir/fakealpm
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

RUN pacman --noconfirm -S curl

RUN pip install hypercorn

# -----------------------------------------------------------------------------

FROM submanager-notconan as submanager-pacman

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

COPY PPpackage-pacman-utils/PPpackage_pacman_utils/ /workdir/PPpackage-pacman-utils/PPpackage_pacman_utils
COPY PPpackage-pacman-utils/setup.py /workdir/PPpackage-pacman-utils/setup.py
RUN pip install PPpackage-pacman-utils/

# -----------------------------------------------------------------------------

FROM submanager-pacman as repository-archlinux

COPY PPpackage-pacman/ /workdir/PPpackage-pacman
RUN pip install PPpackage-pacman/

ENTRYPOINT [ "hypercorn", "PPpackage_submanager.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM base-conan as submanager-conan

RUN pacman --noconfirm -S curl

RUN pip install hypercorn

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-conan/ /workdir/PPpackage-conan/
RUN pip install PPpackage-conan/

ENTRYPOINT [ "hypercorn", "PPpackage_submanager.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM submanager-notconan as submanager-pp

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-PP/ /workdir/PPpackage-PP
RUN pip install PPpackage-PP/

ENTRYPOINT [ "hypercorn", "PPpackage_submanager.server:server", "--bind"]

# -----------------------------------------------------------------------------

FROM submanager-pacman as submanager-aur

COPY PPpackage-AUR/ /workdir/PPpackage-AUR
RUN pip install PPpackage-AUR/

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
RUN mkdir -p /mnt/cache/AUR/ && chown $USER /mnt/cache/AUR/

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-submanager/ /workdir/PPpackage-submanager
RUN pip install PPpackage-submanager/

COPY PPpackage-pacman-utils/PPpackage_pacman_utils/ /workdir/PPpackage-pacman-utils/PPpackage_pacman_utils
COPY PPpackage-pacman-utils/setup.py /workdir/PPpackage-pacman-utils/setup.py
RUN pip install PPpackage-pacman-utils/

COPY PPpackage-pacman/ /workdir/PPpackage-pacman
RUN pip install PPpackage-pacman/

COPY PPpackage-conan/ /workdir/PPpackage-conan
RUN pip install PPpackage-conan/

COPY PPpackage-PP/ /workdir/PPpackage-PP
RUN pip install PPpackage-PP/

COPY PPpackage-AUR/ /workdir/PPpackage-AUR
RUN pip install PPpackage-AUR/

COPY PPpackage/ /workdir/PPpackage
RUN pip install PPpackage/

ENTRYPOINT [ "python", "-m", "PPpackage" ]
