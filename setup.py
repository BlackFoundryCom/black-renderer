from setuptools import setup, find_packages


setup(
    name="blackrenderer",
    use_scm_version={"write_to": "Lib/blackrenderer/_version.py"},
    python_requires=">=3.7",
    package_dir={"": "Lib"},
    packages=find_packages("Lib"),
    install_requires=[
        "fonttools >= 4.17.0",
        "uharfbuzz",
    ],
    extras_require={
        "skia": ["skia-python", "numpy"],
        "cairo": ["pycairo"],
    },
    setup_requires=["setuptools_scm"],
)
