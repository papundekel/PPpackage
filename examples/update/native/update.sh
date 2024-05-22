REPOSITORY=core python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.pacman \
    --index 0 \
    --repository examples/update/repository-pacman.json &

REPOSITORY=extra python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.pacman \
    --index 1 \
    --repository examples/update/repository-pacman.json &

python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.AUR \
    --index 2 &

python -m PPpackage.repository_driver.update \
    PPpackage.repository_driver.conan \
    --index 3 \
    --repository examples/update/repository-conancenter.json &

wait
