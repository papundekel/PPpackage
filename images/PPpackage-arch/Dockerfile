FROM docker.io/greyltc/archlinux-aur:paru-20231203.0.298

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

RUN pacman --noconfirm -S python
RUN pacman --noconfirm -S pacutils
RUN pacman --noconfirm -S pacman-contrib
RUN pacman --noconfirm -S fakeroot
RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S meson

COPY --chown=ab:ab PPpackage-arch/libalpm-pp/ /workdir/libalpm-pp
RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

COPY PPpackage-arch/fakealpm/ /workdir/PPpackage-arch/fakealpm
RUN ./PPpackage-arch/fakealpm/build.sh

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY PPpackage-utils/ /workdir/PPpackage-utils
RUN pip install PPpackage-utils/

COPY PPpackage-arch/PPpackage_arch/ /workdir/PPpackage-arch/PPpackage_arch
COPY PPpackage-arch/setup.py /workdir/PPpackage-arch/setup.py
RUN pip install PPpackage-arch/
