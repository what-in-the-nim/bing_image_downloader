import asyncio
import imghdr
import os
import posixpath
import re
import urllib
import urllib.request
from pathlib import Path
from typing import Literal, Optional

import aiohttp


class Bing:
    def __init__(
        self,
        query: str,
        limit: int,
        output_dir: Optional[str | Path] = None,
        allow_adult_content: bool = False,
        timeout: int = 60,
        filter: Optional[str] = None,
        verbose: bool = True,
    ) -> None:
        """
        Initialize the Bing class

        Parameters:
        ----------
        query: str
            The search query
        limit: int
            The number of images to download
        output_dir: str | Path
            The directory to save the images
        allow_adult_content: bool
            Allow adult content in search results
        timeout: int
            Timeout for image download
        filter: str
            Filter for image search
        verbose: bool
            Enable verbose output
        """
        self.download_count = 0
        self.query = query
        self.output_dir = output_dir
        self.adult: Literal["on", "off"] = "on" if allow_adult_content else "off"
        self.filter = filter
        self.verbose = verbose
        self.seen: set[str] = set()

        self.limit = limit
        self.timeout = timeout

        self.page_counter = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.11 (KHTML, like Gecko) "
            "Chrome/23.0.1271.64 Safari/537.11",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
            "Accept-Encoding": "none",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
        }
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def get_filter(shorthand: str) -> str:
        """Get the filter string for the given shorthand"""
        if shorthand == "line" or shorthand == "linedrawing":
            return "+filterui:photo-linedrawing"
        elif shorthand == "photo":
            return "+filterui:photo-photo"
        elif shorthand == "clipart":
            return "+filterui:photo-clipart"
        elif shorthand == "gif" or shorthand == "animatedgif":
            return "+filterui:photo-animatedgif"
        elif shorthand == "transparent":
            return "+filterui:photo-transparent"
        else:
            return ""

    async def download_image(self, session: aiohttp.ClientSession, link: str) -> None:
        """Download the image from the given link"""
        self.download_count += 1
        try:
            path = urllib.parse.urlsplit(link).path
            filename = posixpath.basename(path).split("?")[0]
            file_type = filename.split(".")[-1]
            if file_type.lower() not in {
                "jpe",
                "jpeg",
                "jfif",
                "exif",
                "tiff",
                "gif",
                "bmp",
                "png",
                "webp",
                "jpg",
            }:
                file_type = "jpg"

            file_path = self.output_dir / f"Image_{self.download_count}.{file_type}"

            async with session.get(link, timeout=self.timeout) as response:
                if response.status == 200:
                    image = await response.read()
                    if not imghdr.what(None, image):
                        print(f"[Error] Invalid image, not saving {link}\n")
                        raise ValueError(f"Invalid image, not saving {link}\n")
                    with open(file_path, "wb") as f:
                        f.write(image)
                else:
                    raise ValueError(f"Failed to download image: {link}")

        except Exception as e:
            self.download_count -= 1
            print(f"[!] Issue getting: {link}\n[!] Error:: {e}")

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch a page from Bing"""
        async with session.get(url, timeout=self.timeout) as response:
            return await response.text()

    async def run(self) -> None:
        """Run the Bing Image Downloader"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while self.download_count < self.limit:
                if self.verbose:
                    print(f"\n\n[!!] Indexing page: {self.page_counter + 1}\n")

                request_url = (
                    "https://www.bing.com/images/async?q="
                    + urllib.parse.quote_plus(self.query)
                    + "&first="
                    + str(self.page_counter)
                    + "&count="
                    + str(self.limit)
                    + "&adlt="
                    + self.adult
                    + "&qft="
                    + ("" if self.filter is None else self.get_filter(self.filter))
                )

                html = await self.fetch_page(session, request_url)
                if not html:
                    print("[%] No more images are available")
                    break

                links = re.findall(r"murl&quot;:&quot;(.*?)&quot;", html)
                if self.verbose:
                    print(
                        f"[%] Indexed {len(links)} Images on Page {self.page_counter + 1}."
                    )
                    print("\n===============================================\n")

                tasks = [
                    self.download_image(session, link)
                    for link in links
                    if self.download_count < self.limit and link not in self.seen
                ]
                self.seen.update(links)
                await asyncio.gather(*tasks)

                self.page_counter += 1
            print(f"\n\n[%] Done. Downloaded {self.download_count} images.")


if __name__ == "__main__":
    from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

    parser = ArgumentParser(
        description="Download images from Bing Image Search",
        
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("limit", type=int, help="Number of images to download")
    parser.add_argument("output_dir", type=Path, help="Directory to save images")
    parser.add_argument(
        "--allow_adult_content",
        action="store_true",
        help="Allow adult content in search results",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Timeout for image download"
    )
    parser.add_argument(
        "--filter", type=str, default="", help="Filter for image search"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    bing = Bing(
        query=args.query,
        limit=args.limit,
        output_dir=args.output_dir,
        allow_adult_content=args.allow_adult_content,
        timeout=args.timeout,
        filter=args.filter,
        verbose=args.verbose,
    )

    asyncio.run(bing.run())
