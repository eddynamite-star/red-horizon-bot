# red_horizon/config.py — consolidated config used across the bot

import os
from datetime import timezone

# --- Timezone object used by tasks/feeds ---
UTC = timezone.utc

# ---------- Tunable knobs (can override via Replit Secrets) ----------
def _env_int(name, default):
    try: return int(os.getenv(name, str(default)))
    except: return default

def _env_float(name, default):
    try: return float(os.getenv(name, str(default)))
    except: return default

def _env_bool(name, default=True):
    val = os.getenv(name)
    if val is None: return default
    return val.strip().lower() in ("1","true","yes","on")

MAX_ITEMS = 7
FRESHNESS_DAYS = 7
SEEN_TTL_DAYS = 14

BREAKING_MAX_AGE_MIN = _env_int("BREAKING_MAX_AGE_MIN", 60)
BREAKING_MIN_SCORE   = _env_float("BREAKING_MIN_SCORE", 1.5)
SUPER_COOLDOWN_MIN   = _env_int("SUPER_COOLDOWN_MIN", 5)
ENABLE_SUPER_PRIORITY = _env_bool("ENABLE_SUPER_PRIORITY", True)

# ---------- Keywords ----------
KEYWORDS = [
    # SpaceX / Starship
    "spacex","starship","starbase","boca chica","falcon 9","falcon-9","falcon9",
    "super heavy","booster","mechazilla","chopsticks","orbital launch mount",
    "wide bay","mega bay","high bay","starfactory","raptor","merlin",
    "dragon","crew dragon","cargo dragon",
    # Mars / missions
    "mars","terraform","habitat","red planet","isru","mars sample return",
    # Agencies / programs
    "nasa","esa","jpl","hubble","jwst","james webb","orion","sls","iss",
    # Industry
    "ula","vulcan","rocket lab","electron","neutron",
    "blue origin","new shepard","new glenn","arianespace","ariane 6","vega",
    "relativity","terran r","firefly","alpha"
]

STARBASE_KEYWORDS = [
    "starbase","boca chica","olp","olm","orbital launch mount","launch tower",
    "mechazilla","chopsticks","catch arms","high bay","mega bay","wide bay",
    "starfactory","propellant farm","suborbital pad","pad a","pad b",
    "booster","ship","stack","destack","rollout","rollback",
    "static fire","hotfire","wdr","wet dress","cryoproof","cryogenic test","road closure"
]

PRIORITY_KEYWORDS = [
    "launch","liftoff","static fire","hotfire","wdr","wet dress",
    "stack","destack","rollout","rollback","engine test","anomaly","scrub","delay","countdown","live","upcoming","premiere"
]

NEGATIVE_HINTS = ["opinion","editorial","sponsored","weekly","roundup","recap","feature","podcast","newsletter"]

# ---------- Provider weights & high-signal domains ----------
PROVIDER_WEIGHTS = {
    # trade/press
    "nasaspaceflight.com": 2.5,
    "spacenews.com": 2.0,
    "spaceflightnow.com": 2.0,
    "arstechnica.com": 1.8,
    "space.com": 1.3,
    "everydayastronaut.com": 1.3,
    "whataboutit.space": 1.0,
    "universetoday.com": 1.0,
    "scientificamerican.com": 1.0,
    # official / agencies
    "nasa.gov": 2.5,
    "jpl.nasa.gov": 2.3,
    "esa.int": 2.0,
    "global.jaxa.jp": 1.8,
    # company
    "spacex.com": 2.5,
    "rocketlabusa.com": 1.8,
    "blueorigin.com": 1.8,
    "arianespace.com": 1.6,
    "ulalaunch.com": 1.5,
    "youtube.com": 1.0,
}

HIGH_SIGNAL_DOMAINS = [
    "nasaspaceflight.com","spaceflightnow.com","everydayastronaut.com","spacex.com"
]

# ---------- Feeds ----------
FEEDS = list(set([
    # Spaceflight / industry
    "https://www.nasaspaceflight.com/feed/",
    "https://everydayastronaut.com/feed/",
    "https://www.whataboutit.space/feed/",
    "https://spaceflightnow.com/feed/",
    "https://www.space.com/feeds/all",
    "https://spacenews.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/space",
    "https://www.universetoday.com/feed/",
    "https://www.thespacereview.com/rss.xml",
    "https://www.scientificamerican.com/feed/space/",
    "https://phys.org/rss-feed/space-news/",
    # Agencies
    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    "https://science.nasa.gov/feed/",
    "https://mars.nasa.gov/rss/news",
    "https://www.esa.int/rssfeed",
    "https://www.jpl.nasa.gov/feeds/news.xml",
    "https://global.jaxa.jp/rss/rss.xml",
    "https://www.eso.org/public/rss/press-releases/",
    # Launch providers
    "https://www.arianespace.com/feed/",
    "https://blog.rocketlabusa.com/rss",
    "https://www.blueorigin.com/news/rss",
    "https://www.ulalaunch.com/rss/press-releases.xml",
]))

IMAGE_FEEDS = list(set([
    "https://apod.nasa.gov/apod.rss",
    "https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss",
    "https://www.esa.int/rssfeed/ESA_Multimedia_Images",
    "https://hubblesite.org/rss/news",
    "https://earthobservatory.nasa.gov/feeds/eo.rss",
    "https://www.universetoday.com/feed/",
    # RGV & Andrew McCarthy (Flickr public feeds)
    "https://www.flickr.com/services/feeds/photos_public.gne?id=154560776@N07&lang=en-us&format=rss_200",
    "https://www.flickr.com/services/feeds/photos_public.gne?id=182367180@N05&lang=en-us&format=rss_200",
]))

# YouTube feeds for super-priority signals (SpaceX/NSF/Everyday Astronaut)
YOUTUBE_FEEDS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCtI0Hodo5o5dUb67FeUjDeA",  # SpaceX
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCSUu1lih2RifWkKtDOJdsBA",  # NASA Spaceflight
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC6uKrU_WqJ1R2HMTY3LIx5Q",  # Everyday Astronaut
]

# ---------- Copy / UI ----------
HASHTAG_LINE = "#Mars #SpaceX #Starship #RedHorizon"

WELCOME_MESSAGE = (
    "👋 *Welcome to Red Horizon*\n\n"
    "Your daily hub for Mars & SpaceX news, exploration, Starbase, and sci-fi culture.\n\n"
    "Expect:\n"
    "• 🚀 Daily digests\n"
    "• 📰 Breaking news\n"
    "• 🛠 Starbase updates & 🏗 highlights\n"
    "• 📸 Daily images (NASA/APOD/ESA + creators)\n"
    "• 📖 Book spotlights (TG-exclusive)\n\n"
    "Follow on X: @RedHorizonHub\n"
    "Invite: https://t.me/RedHorizonHub\n\n"
    "#Mars #SpaceX #Terraforming #SciFi #RedHorizon"
)
