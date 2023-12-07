FROM docker.io/greyltc/archlinux-aur:paru-20231203.0.298

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

RUN pacman --noconfirm -S python

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY PPpackage-utils/ /workdir/packages/PPpackage-utils/
RUN pip install packages/PPpackage-utils/

COPY PPpackage-PP/ /workdir/packages/PPpackage-PP/
RUN pip install packages/PPpackage-PP/
