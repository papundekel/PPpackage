FROM docker.io/greyltc/archlinux-aur:paru-20231105.0.294

RUN mkdir --parents /workdir
WORKDIR /workdir

RUN pacman --noconfirm --sync --refresh --sysupgrade

RUN pacman --noconfirm --sync python
RUN pacman --noconfirm --sync runc
RUN pacman --noconfirm --sync --refresh --sysupgrade podman

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY PPpackage-utils/ /workdir/packages/PPpackage-utils/
RUN pip install packages/PPpackage-utils/

COPY PPpackage-runner/ /workdir/packages/PPpackage-runner/
RUN pip install packages/PPpackage-runner/

RUN mkdir --parents --mode 777 /workdir/PPpackage-runner
