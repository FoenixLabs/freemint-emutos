#!/bin/bash
# Convenience script for building
pushd foenix
rm libfoenix.a
make -j4
popd
rm -f emutos.img emutos-a2560m.rom
# Change "fr" to your country code and 4 to the number of CPU cores you have
# Please note that is not the A2560m anymore, it is the A2560Me
make UNIQUE=us a2560m -j4
