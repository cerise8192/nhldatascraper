Note: SMT has changed format and data is distributed now via NHL edge instead
of this platform, so this is broken now.

This will download the NHL data from the statsapi, htmlevents, and nhle and collate it.
See 2023/02/0001 for the first game of the 2023-24 regular season.

Run this by doing:
$ ./getnhlgamedata.py $tag

The tag consists of the first year of the season (i.e. 2015-2016 would be
2015), the season type (01 for preseason, 02 for regular season, 03 for
playoffs), and the game ID.  The game IDs are sequential in 01 & 02, but
they're stored differently for the playoffs where 0315 is the 5th game in
the 1st matchup of the 3rd round of the playoffs.
