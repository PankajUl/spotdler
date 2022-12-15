"""
Sync Lyrics module for the console
"""

from pathlib import Path
from typing import List

from spotdl.download.downloader import Downloader
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.metadata import embed_metadata, get_file_metadata
from spotdl.utils.search import get_search_results, get_song_from_file_metadata


def meta(query: List[str], downloader: Downloader, **_) -> None:
    """
    This function applies metadata to the selected songs
    based on the file name.
    If song already has metadata, missing metadata is added

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.

    ### Notes
    - This function is multi-threaded.
    """

    # Create a list of all songs from all paths in query
    paths: List[Path] = []
    for path in query:
        test_path = Path(path)
        if not test_path.exists():
            downloader.progress_handler.error("Path does not exist: " + path)
            continue

        if test_path.is_dir():
            for out_format in FFMPEG_FORMATS:
                paths.extend(test_path.glob(f"*.{out_format}"))
        elif test_path.is_file():
            if test_path.suffix.split(".")[-1] not in FFMPEG_FORMATS:
                downloader.progress_handler.error(
                    "File is not a supported audio format: " + path
                )
                continue

            paths.append(test_path)

    def process_file(file: Path):
        song_meta = get_file_metadata(file)

        if (
            song_meta
            and song_meta["lyrics"] is not None
            and song_meta["title"][0] != ""
        ):
            downloader.progress_handler.log("Song already has metadata: " + file.name)
            return None

        # Check if we have metadata if not use spotify
        # to get the metadata
        try:
            if (
                song_meta is None
                or song_meta["title"][0] == ""
                or song_meta["tracknumber"][0] == ""
            ):
                song = get_song_from_file_metadata(file)
                if song is None:
                    raise Exception
            else:
                raise Exception
        except Exception:
            search_results = get_search_results(file.stem)
            if not search_results:
                downloader.progress_handler.error(
                    f"Could not find metadata for {file.name}"
                )
                return None

            song = search_results[0]

        # Check if the song has lyric
        # if not use downloader to find lyrics
        if song_meta is None or song_meta.get("lyrics") is None:
            downloader.progress_handler.debug(
                f"Fetching lyrics for {song.display_name}"
            )
            lyrics = downloader.search_lyrics(song)
            if lyrics:
                song.lyrics = lyrics
                downloader.progress_handler.log(
                    f"Found lyrics for song: {song.display_name}"
                )

        # Apply metadata to the song
        embed_metadata(file, song)

        downloader.progress_handler.log(f"Applied metadata to {file.name}")

        return None

    async def pool_worker(file_path: Path) -> None:
        async with downloader.semaphore:
            # The following function calls blocking code, which would block whole event loop.
            # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
            # is not a problem, since GIL is released for the I/O operations, so it shouldn't
            # hurt performance.
            await downloader.loop.run_in_executor(
                downloader.thread_executor, process_file, file_path
            )

    tasks = [pool_worker(path) for path in paths]

    # call all task asynchronously, and wait until all are finished
    downloader.loop.run_until_complete(downloader.aggregate_tasks(tasks))
