KModGen
-------

KModGen is a bunch of scripts, written in Python, to generate 3D models and footprints for KiCad.

Features
--------

* Generates 3D-models for:
  - radial capacitors;
  - QFP and SOP packages;
  - Pin Headers and Box Headers.
* Generates footprints for:
  - radial capacitors;
  - tantalum chip capacitors;
  - QFP and SOP packages;
  - Pin Headers and Box Headers;
  - Chip resistors and capacitors;
  - SOT.
* Internal viewer for VRML and X3D models.

Installation
------------

Scripts require Python 2.7 or Python 3 with NumPy and lxml packages. Internal X3D/VRML viewer is optional and requires Pillow and OpenGL packages.

Now you are ready to clone the repository:

```sh
git clone https://github.com/stxent/kmodgen.git
cd kmodgen
git submodule update --init --recursive
```

Quickstart
----------

Build all footprints and models from descriptions directory, output format is S-Expression for footprints and X3D for models, all files will be installed in the specified directory:

```sh
mkdir build
cd build
cmake .. -DUSE_PRETTY=ON -DUSE_X3D=ON -DCMAKE_INSTALL_PREFIX=~/kicad
make install
```
