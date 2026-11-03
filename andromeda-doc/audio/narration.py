# Narration lines from PLAN.md: (chapter, offset_s, text). Absolute time = (chapter-1)*60 + offset.
LINES = [
 (1, 2.0, "Look up on a dark autumn night, far from city lights."),
 (1, 7.5, "Near the constellation Andromeda, there's a faint smudge. Most people never notice it."),
 (1, 15.0, "It isn't a cloud. It isn't a star. It's another galaxy — a spiral of perhaps a trillion suns."),
 (1, 24.0, "If your eyes could gather enough light, it would stretch across the sky, about six full Moons wide."),
 (1, 33.0, "The light you're seeing left it two and a half million years ago — before our species existed."),
 (1, 43.0, "It is the farthest thing most of us will ever see with our own eyes."),
 (1, 51.0, "And it is coming toward us."),
 (2, 1.0, "In 1912, astronomer Vesto Slipher measured its light — and found it shifted toward blue."),
 (2, 9.0, "Andromeda was approaching. Today we know it's closing at about a hundred and ten kilometres every second."),
 (2, 18.5, "Four hundred thousand kilometres every hour. Roughly the distance to the Moon."),
 (2, 26.0, "For decades, astronomers thought a head-on collision was certain."),
 (2, 32.0, "But measuring its sideways drift is extraordinarily hard."),
 (2, 37.5, "Recent studies using the Hubble and Gaia spacecraft disagree: some give it a coin-flip chance of merging within ten billion years; newer work puts it closer to ninety percent."),
 (2, 50.0, "So let's follow the version where it comes."),
 (3, 1.0, "In about two billion years, it would no longer be a smudge."),
 (3, 8.0, "Night after night, nothing would seem to change. But over millions of years, it would swell."),
 (3, 17.0, "Its spiral arms, its dark lanes of dust, its glowing core — all visible to the naked eye."),
 (3, 26.0, "Some four billion years from now, it could fill the sky — a second galaxy, hanging over the horizon."),
 (3, 37.0, "Then our own Milky Way would begin to bend, pulled out of shape by the gravity of its neighbour."),
 (3, 47.0, "Two galaxies, a hundred billion stars and more each, falling into one another."),
 (4, 1.0, "And yet, almost no stars would collide. The space between them is simply too vast."),
 (4, 9.5, "But the clouds of gas would. They'd crash together and ignite, lighting the sky with newborn stars."),
 (4, 19.0, "Over billions of years, the two spirals would settle into one great, glowing elliptical galaxy."),
 (4, 28.0, "Astronomers already have a name for it: Milkomeda."),
 (4, 34.0, "Our Sun would likely survive — perhaps flung to a new orbit, far from where it is today."),
 (4, 42.0, "But no one on Earth will see it. Long before then, the Sun will have grown too bright for oceans, or for us."),
 (4, 52.0, "Someone, somewhere, may be watching. It won't be us."),
]
# Text actually sent to TTS (pronunciation help only; subtitles use LINES text).
TTS_OVERRIDES = {
 "In 1912,": "In nineteen twelve,",
 "Slipher": "Slyfer",              # pronounced SLY-fer
}
# Phoneme fixes applied after espeak phonemisation (Milkomeda = milk-OM-eh-da, like Andromeda).
PHONEME_FIXES = {
 "mˈɪlkoʊmdə": "mˌɪlkˈɑːmɪdə",
}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
