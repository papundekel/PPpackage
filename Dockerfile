FROM greyltc/archlinux-aur:paru

RUN mkdir -p /workdir

RUN pacman --noconfirm -Syu pacutils pacman-contrib python

RUN aur-install bindfs conan

RUN pacman --noconfirm -S fakeroot fakechroot

RUN pacman --noconfirm -S yajl

RUN pacman --noconfirm -S cmake

RUN pacman --noconfirm -Syu python-typer

RUN pacman --noconfirm -Syu meson

WORKDIR /workdir

COPY --chown=ab:ab ./libalpm-pp /workdir/libalpm-pp 

RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

COPY ./fakealpm/ /workdir/fakealpm

RUN cd fakealpm && gcc -shared -fPIC -o build/fakealpm.so -I /usr/share/libalpm-pp/usr/include/ fakealpm.c

COPY ./*.jinja ./profile /workdir/

COPY --chmod=a+x ./*.py ./*.sh /workdir/
