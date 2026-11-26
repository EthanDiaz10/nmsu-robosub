#!/bin/bash
# Usage: ./run_case.sh <speed m/s> <name> [iters]   (flow +X = vehicle surging forward, -X)
# Needs a meshed base case in ./case (blockMesh + snappyHexMesh already done).
set -e
U=$1; NAME=$2; IT=${3:-800}; AREF=${AREF:-0.06453}
export WM_PROJECT_DIR=/usr/share/openfoam FOAM_ETC=/usr/share/openfoam/etc
rm -rf $NAME; mkdir $NAME; cp -r case/system case/constant $NAME/; cd $NAME
K=$(python3 -c "print(f'{1.5*(0.01*$U)**2:.4e}')"); OM=$(python3 -c "print(f'{2.24*$U:.4g}')")
cp -r ../case/0.orig 0
sed -i "s/UX/$U/g; s/UY/0/g; s/UZ/0/g" 0/U; sed -i "s/KIN/$K/g" 0/k; sed -i "s/OMIN/$OM/g" 0/omega
sed -i "s/endTime 800/endTime $IT/" system/controlDict
decomposePar -force > log.decompose 2>&1
mpirun --allow-run-as-root --oversubscribe -np 4 simpleFoam -parallel > log.simpleFoam 2>&1
reconstructPar -latestTime > log.reconstruct 2>&1
