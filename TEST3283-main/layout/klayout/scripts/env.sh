# Clean KLayout environment: only the pinned PDK tree is visible (no ~/.klayout, no $PDK_ROOT).
# PDK_TREE defaults to the origin/dev review worktree; override to rebuild against another tree.
PDK_TREE=${PDK_TREE:-/home/montanares/git/IHP-Open-PDK-worktrees/cap-momi-em-review}
KHOME=${KHOME:-$(mktemp -d)}
# One thread per BLAS/OpenMP user: unset, OpenBLAS spawns a spinning worker per core (shared machine).
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
kl() {
    env -u KLAYOUT_PATH KLAYOUT_HOME="$KHOME" KLAYOUT_PATH="$PDK_TREE/ihp-sg13cmos5l/libs.tech/klayout" \
        PDK_ROOT="$PDK_TREE" PDK=ihp-sg13cmos5l klayout "$@"
}
