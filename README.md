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

Scripts require python-2.7, python-numpy, python-xml and python-lxml packages. Internal X3D/VRML viewer is optional, python-imaging and python-opengl packages are needed for it to work.

Now you are ready to clone the repository:

```sh
git clone https://github.com/stxent/kmodgen.git
cd kmodgen
git submodule update --init --recursive
```

Quickstart
----------

Complete list of commands to process available descriptions, generate VRML models and put them in a temporary directory:

```sh
mkdir temp
./mod.py -i descriptions/capacitors.json -m descriptions/capacitors_mat.json -f wrl -o temp
./mod.py templates/headers.x3d -i descriptions/headers.json -f wrl -o temp
./mod.py templates/smd_qfp.x3d -i descriptions/smd_qfp.json -f wrl -o temp
./mod.py templates/smd_sop.x3d -i descriptions/smd_sop.json -f wrl -o temp
```

Examples
--------

Generate 3D models for QFP packages using a template model and export them to X3D:

```sh
./mod.py templates/smd_qfp.x3d -i descriptions/smd_qfp.json -f x3d -o temp
```

View model in the internal viewer (requires PyOpenGL):

```sh
wrlconv/wrload.py --grid -v temp/lqfp64.wrl
```

