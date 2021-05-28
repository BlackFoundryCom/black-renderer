[![Python package](https://github.com/BlackFoundryCom/black-renderer/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackFoundryCom/black-renderer/actions/workflows/ci.yml)

# BlackRenderer

Developing a Python-based renderer for OpenType COLRv1 fonts, with multiple backends.

![Big Smiley Face Icon](https://github.com/BlackFoundryCom/black-renderer/blob/master/smile.png?raw=true)

## Goals

- Use fonttools to parse COLRv1 data
- Adapter classes for various 2D rendering back-ends:
  1. Debugging/printing (text dump of scene graph / 2D API calls)
  2. skia-python
  3. pycairo
  4. SVG
  6. CoreGraphics (macOS)
  7. ...
- hb-view-like command line app with switchable backend

## Usage

BlackRenderer comes with an hb-view-like command line tool, that can be used like this:

    $ blackrenderer font.ttf ABC🤩 output.png --font-size=100

## Install

If you have a Python 3 environment set up, then all you need to do is:

	$ pip install blackrenderer

## Install for contributing / setting up an environment

Have Python 3.7 or higher installed.

Open Terminal.

"cd" into the project repo directory.

Create a virtual environment:

- `$ python3 -m venv venv --prompt=black-renderer`

Activate the venv:

- `$ source venv/bin/activate`

(You need to activate the virtual environment for every new terminal session.)

Upgrade pip:

- `$ pip install --upgrade pip`

Install the requirements:

- `$ pip install -r requirements.txt`
- `$ pip install -r requirements-dev.txt`

Install blackrenderer in editable mode:

- `$ pip install -e .`

Run the tests:

- `$ pytest`

## Maintainers: how to release

To cut a release, make an annotated git tag, where the tag is in this format:
v1.2.3, where 1, 2 and 3 represent major, minor and micro version numbers.
You can add "aN" or "bN" or "rc" to mark alpha, beta or "release candidate"
versions. Examples: v1.2.3, v1.2.3b2, v1.2.3a4, v1.2.3rc.

The message for the annotated tag should contain the release notes.

Then use "git push --follow-tags" to trigger the release bot. Example session:

- `$ git tag -a v1.2.3 -m "v1.2.3 -- fixed issue #12345"`
- `$ git push --follow-tags`

This process will create a GitHub release, as well as upload the package to
PyPI.
