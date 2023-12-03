FROM greyltc/archlinux-aur:paru-20231203.0.298

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

RUN pacman --noconfirm -S python
RUN pacman --noconfirm -S pacutils
RUN pacman --noconfirm -S pacman-contrib
RUN pacman --noconfirm -S fakeroot
RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S meson

COPY --chown=ab:ab ./libalpm-pp /workdir/libalpm-pp 
RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

COPY fakealpm/ /workdir/fakealpm
RUN ./fakealpm/build.sh

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY PPpackage-utils/ /workdir/packages/PPpackage-utils/
RUN pip install packages/PPpackage-utils/

COPY PPpackage-arch/ /workdir/packages/PPpackage-arch/
RUN pip install packages/PPpackage-arch/
