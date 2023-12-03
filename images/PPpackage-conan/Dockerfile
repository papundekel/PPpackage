FROM greyltc/archlinux-aur:paru-20231203.0.298

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

RUN pacman --noconfirm -S python
RUN aur-install conan

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY PPpackage-utils/ /workdir/packages/PPpackage-utils/
RUN pip install packages/PPpackage-utils/

COPY PPpackage-conan/ /workdir/packages/PPpackage-conan/
RUN pip install packages/PPpackage-conan/
