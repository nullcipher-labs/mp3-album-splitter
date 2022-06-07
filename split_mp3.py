from pydub import AudioSegment
import os
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TPE2, COMM, TCOM, TCON, TDRC, TRCK, APIC


class Track:
    def __init__(self, data, num, sep1=':', sep2=' '):
        """
        a class representing a single track to be split from the source audio

        :param data: track info, assumed to be of the format '<start time> <track name>', e.g. '00:30 Red Sky'
        :param num: the track number in the album
        :param sep1: the separator in the time format, e.g. ':' in '00:30'
        :param sep2: the separator between the time stamp and the title, e.g. ' ' in '00:30 Red Sky'
        """
        ind = data.find(sep2)
        t1, t2 = data[:ind], data[ind+1:]

        self.num = num
        self.title = t2

        self.start_time = self.time_to_ms(t1, sep1)

        # usually left None and updated as the next track's start time
        self.end_time = None

    def __repr__(self):
        return f'{self.num}. {self.title}'

    def __lt__(self, other):
        # used for sorting tracks in album, by track number
        return self.num < other.num

    @staticmethod
    def time_to_ms(time_string, sep):
        """
        takes a time signature of the form hh:mm:ss and converts it to milliseconds
        e.g. '01:33:20' => 5600000

        :param time_string: time signature string, e.g. '03:55'
        :param sep: the separator in the time format, e.g. in 02:03 the sep is ':'
        :return: int, time in milliseconds
        """
        l = time_string.split(sep)

        # count how many separators are there to check if there are more than 0 hours
        sep_count = time_string.count(sep)
        hours = 0
        if sep_count == 1:
            mins = int(l[0])
            secs = int(l[1])
        elif sep_count == 2:
            hours = int(l[0])
            mins = int(l[1])
            secs = int(l[2])
        else:
            raise ValueError(f'number of {sep} in timestamp {time_string} is invalid ({sep_count})')

        return (secs + mins*60 + hours*60*60) * 1000


class Album:
    def __init__(self, filepath, audio_path, name, artist='', output_path='', cover_path=None, sep1=':', sep2=' '):
        """
        a class representing an album, a collection of tracks to be split from the source audio

        :param filepath: path to the txt file containing the track names and times
        :param audio_path: path to the source mp3 file
        :param name: album name (for track meta-data)
        :param artist: album artist (for track meta-data)
        :param output_path: path to put the split mp3s in
        :param cover_path: path to the photo cover art
        :param sep1: the separator in the time format, e.g. ':' in '00:30' (in the txt)
        :param sep2: the separator between the time stamp and the title, e.g. ' ' in '00:30 Red Sky' (in the txt)
        """
        self.audio_path = audio_path
        self.name = name
        self.artist = artist
        self.output_path = output_path
        self.cover_path = cover_path
        self.tracks = []

        with open(filepath, 'r') as f:
            i = 1
            for line in f:
                self.tracks.append(Track(line.strip(), i, sep1, sep2))
                i += 1

        # add the end time to each track, copied from the start time of the track after it
        self.add_end_times()

    def add_end_times(self):
        for i in range(len(self.tracks)-1):
            self.tracks[i].end_time = self.tracks[i+1].start_time

    def __len__(self):
        return len(self.tracks)


def split_mp3(album, to_print=True):
    """
    splits a source mp3 track to an album, based on an Album instance

    :param album: an Album instance
    :param to_print: a boolean, if True the function will print messages indicating progress
    """
    source = AudioSegment.from_mp3(album.audio_path)
    overall = len(album)  # number of tracks

    if to_print:
        print(f'SPLITTING ALBUM: {album.name}...')

    # all but the last track, cause it doesn't end at the start time of the track after it
    i = 1
    for track in album.tracks[:-1]:
        cur_song = source[track.start_time:track.end_time]
        cur_song.export(f'{album.output_path}\\{str(track)}.mp3', format="mp3")

        if to_print:
            print(f'{str(track)}.mp3 >> SPLIT ({i}/{overall})')
            i += 1

    # handling end time for last track and exporting it
    last = album.tracks[-1]
    last_song = source[last.start_time:]
    last_song.export(f'{album.output_path}\\{str(last)}.mp3', format="mp3")

    if to_print:
        print(f'{str(last)}.mp3 >> SPLIT ({i}/{overall})')


def edit_meta(song_path, title, artist, album, track_num, cover):
    """
    edits the meta data of a single mp3 track

    :param song_path: mp3 file path
    :param title: new title
    :param artist: new artist
    :param album: new album name
    :param track_num: new track num
    :param cover: new cover art
    """
    try:
        tags = ID3(song_path)
    except ID3NoHeaderError:
        tags = ID3()

    # update title, artist, album, track num
    tags["TIT2"] = TIT2(encoding=3, text=title)
    tags["TPE1"] = TPE1(encoding=3, text=artist)
    tags["TALB"] = TALB(encoding=3, text=album)
    tags["TRCK"] = TRCK(encoding=3, text=str(track_num))
    tags.save(song_path)

    # update cover art, if one was provided
    if cover is not None:
        audio = MP3(song_path, ID3=ID3)
        audio.tags.add(
            APIC(
                encoding=3,
                mime=f'image/{os.path.splitext(cover)[1]}',
                type=3,
                desc=u'Cover',
                data=open(cover, 'rb').read()
            )
        )
        audio.save(v2_version=3)


def edit_album_meta(album, to_print=True):
    """
    edits the meta data for all the tracks in a given album

    :param album: an Album instance
    :param to_print: a boolean, if True the function will print messages indicating progress
    """
    if to_print:
        print('\nEDITING META DATA...')

    count = 1  # for track numbering
    overall = len(album.tracks)  # number of tracks

    # go over the files in the output folder
    for path, dirs, files in os.walk(album.output_path):
        # sort the files by track number
        files.sort(key=get_track_num)

        # go over both the sorted files, and the track objects in the album, in tandem
        for file, track in zip(files, album.tracks):
            if file[-3:] == 'mp3':
                cur_path = os.path.join(path, file)
                edit_meta(cur_path, track.title, album.artist, album.name, count, album.cover_path)

                if to_print:
                    print(f"{str(track)}.mp3 >> DONE ({count}/{overall})")

                count += 1


def get_info(info_path):
    """
    goes over the configuration text file and extracts the relevant data
    :param info_path: path to the config file
    :return: a tuple including: (audio_path, tracklist_path, cover_path, output_path, name, artist)
    """
    lines = []
    with open(info_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line == '':
                continue

            if line[0] == '"':
                line = line.strip('"')

            lines.append(line)

    return tuple(lines)


def get_track_num(song_name):
    """
    gets the track number from a song file name, e.g. '05. Swim.mp3' => 5

    :param song_name: string, song file name
    :return: int, track number
    """
    ind = song_name.find('.')
    return int(song_name[:ind])


if __name__ == '__main__':
    # get config data
    audio_path, tracklist_path, cover_path, \
    output_path, name, artist = get_info(r"split_mp3_config.txt")

    # create album
    A = Album(tracklist_path, audio_path, name, artist, output_path, cover_path, ':', ' ')

    # split audio to tracks and edit meta data
    split_mp3(A)
    edit_album_meta(A)

    input('\nPress any key to exit...')
