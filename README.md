# mp3-album-splitter
A python program to split a single mp3 file into multiple tracks, and edit their metadata automatically. Used for splitting albums downloaded from youtube.

Ever wanted to turn one of those youtube videos with a full album in one vid, into an mp3 playlist on your pc?
If you can download such a vid and convert it into a single mp3, and you have a list of track names with corresponding video times - this script will split the source audio file into those tracks for you, naming and numbering them automatically, and adding metadata like album name, artist and cover art.

You can find an example config text file here, as well as the python code.
See instructions pdf for how to use.

# prerequisites
pydub<br>https://pypi.org/project/pydub/<br>pip install pydub
<br><br>
mutagen<br>https://pypi.org/project/mutagen/<br>pip install mutagen
