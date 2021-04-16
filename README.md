# BlackRenderer

Developing a pure Python renderer for COLRv1 fonts.

## Goals

- Uses fonttools to parse COLRv1 data
- Adapter classes for various 2D rendering back-ends:
  1. DrawBot
  2. Cocoa
  2. skia-python
  3. pycairo
  4. ?

## Install / Setting up an environment

Have Python 3.7 or higher installed, preferably from [python.org](https://www.python.org)

Open Terminal

"cd" into the project repo directory

Create a virtual environment:

- `$ python3 -m venv venv --prompt=black-renderer`

Activate the venv:

- `$ source venv/bin/activate`

(You need to activate the virtual environment for every new terminal session.)

Upgrade pip

- `$ pip install --upgrade pip`

Install the requirements:

- `$ pip install -r requirements.txt`
- `$ pip install -r requirements-dev.txt`

Install blackrenderer in editable mode:

- `$ pip install -e .`

Run the tests:

- `$ pytest`
