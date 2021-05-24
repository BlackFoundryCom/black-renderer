import os
import pathlib
import subprocess
import pytest


dataDir = pathlib.Path(__file__).resolve().parent / "data"


testData = [
    ("ABC", dataDir / "MutatorSans.ttf"),
    ("\u2693\u2694", dataDir / "noto-glyf_colr_1.ttf"),
    ("\u3299", dataDir / "TwemojiMozilla.subset.default.3299.ttf"),
]


@pytest.mark.parametrize("testString, fontPath", testData)
@pytest.mark.parametrize("outputFormat", [".png", ".svg"])
def test_mainprog(tmpdir, testString, fontPath, outputFormat):
    outputPath = os.path.join(tmpdir, "test" + outputFormat)
    args = [
        "blackrenderer",
        os.fspath(fontPath),
        testString,
        outputPath,
        "--font-size",
        "50",
    ]
    subprocess.check_output(args)
    assert os.path.isfile(outputPath)
