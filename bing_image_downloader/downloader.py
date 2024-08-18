import shutil
import sys
from pathlib import Path

from .bing import Bing


def download(
    query: str,
    limit: int = 100,
    output_dir: str = "dataset",
    adult_filter_off: bool = True,
    force_replace: bool = False,
    timeout: int = 60,
    filter: str = "",
    verbose: bool = True,
) -> None:
    """Download images from Bing Image Search"""
    # engine = 'bing'
    if adult_filter_off:
        adult = "off"
    else:
        adult = "on"

    image_dir = Path(output_dir).joinpath(query).absolute()

    if force_replace:
        if Path.is_dir(image_dir):
            shutil.rmtree(image_dir)

    # check directory and create if necessary
    try:
        if not Path.is_dir(image_dir):
            Path.mkdir(image_dir, parents=True)

    except Exception as e:
        print("[Error]Failed to create directory.", e)
        sys.exit(1)

    print("[%] Downloading Images to {}".format(str(image_dir.absolute())))
    bing = Bing(query, limit, image_dir, adult, timeout, filter, verbose)
    bing.run()


if __name__ == "__main__":
    download("dog", output_dir="..\\Users\\cat", limit=10, timeout=1)
