from PIL import Image, ImageChops


def compareImages(path1, path2):
    """Compare two image files and return a number representing how similar they are.
    A value of 0 means that the images are identical, a value of 1 means they are maximally
    different or not comparable (for example, when their dimensions differ).
    """
    assert path1.suffix == path2.suffix
    if path1.suffix.lower() == ".svg":
        if compareFiles(path1, path2):
            return 1
        else:
            return 0

    im1 = Image.open(path1)
    im2 = Image.open(path2)

    if im1.size != im2.size:
        # Dimensions differ, can't compare further
        return 1

    if im1 == im2:
        # Image data is identical (I checked PIL's Image.__eq__ method: it's solid)
        return 0

    # Get the difference between the images
    diff = ImageChops.difference(im1, im2)

    # We'll calculate the average difference based on the histogram provided by PIL
    hist = diff.histogram()
    assert (
        len(hist) == 4 * 256
    )  # Assuming 4x8-bit RGBA for now. TODO: make this work for L and RGB modes
    # Sum the histograms of each channel
    summedHist = [
        sum(hist[pixelValue + ch * 256] for ch in range(4)) for pixelValue in range(256)
    ]

    assert len(summedHist) == 256
    assert sum(hist) == sum(summedHist)
    # Calculate the average of the difference
    # First add all pixel values together
    totalSum = sum(summedHist[pixelValue] * pixelValue for pixelValue in range(256))
    # Then divide by the total number of channel values
    average = totalSum / sum(summedHist)
    # Scale pixel value range from 0-255 to 0-1
    average = average / 255
    assert 0.0 <= average <= 1.0
    return average


def compareFiles(path1, path2):
    return path1.read_bytes() != path2.read_bytes()
