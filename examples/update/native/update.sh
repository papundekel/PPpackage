REPOSITORY=core python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.pacman \
    archlinux-core \
    --repository-config examples/update/repository-pacman.json &

REPOSITORY=extra python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.pacman \
    archlinux-extra \
    --repository-config examples/update/repository-pacman.json &

python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.AUR \
    AUR &

python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.conan \
    conancenter \
    --repository-config examples/update/repository-conancenter.json &

wait
