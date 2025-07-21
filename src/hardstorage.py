import json

POPULAR_EVENT_IDS = ["333", "222", "444", "pyram", "skewb"]

WEEK_1 = ["555","333oh","clock","minx","666"]
WEEK_2 = ["555","333oh","clock","333bf","777"]
WEEK_3 = ["555","333oh","clock","sq1","234"]

ALL_WEEKS = [WEEK_1, WEEK_2, WEEK_3]

DICTIONARY = {
    "222": "2x2x2",
    "333": "3x3x3",
    "444": "4x4x4",
    "555": "5x5x5",
    "666": "6x6x6",
    "777": "7x7x7",
    "333oh": "3x3x3 One-Handed",
    #"333bld": "3x3x3 Blindfolded",
    "333bf": "3x3x3 Blindfolded",
    "333mbf": "3x3x3 Multi-Blindfolded",
    "333fm":"3x3x3 Fewest moves",
    #"444bld": "4x4x4 Blind",
    "444bf": "4x4x4 Blindfolded",
    "555bf": "5x5 Blindfolded",
    "pyram": "Pyraminx",
    "skewb": "Skewb",
    "clock": "Clock",
    "minx": "Megaminx",
    "sq1": "Square-1",
    "234": "2+3+4 Relay",
    #* separator --------------------------------
    "333ft":"3x3x3 Feet"
}

SHORT_DICTIONARY = {
    "222": "2x2",
    "333": "3x3",
    "444": "4x4",
    "555": "5x5",
    "666": "6x6",
    "777": "7x7",
    "333oh": "3x3 OH",
    #"333bld": "3x3x3 Blindfolded",
    "333bf": "3x3 Blind",
    "333mbf": "3x3 Multi Blind",
    "333fm":"3x3 FMC",
    #"444bld": "4x4x4 Blind",
    "444bf": "4x4 Blind",
    "555bf": "5x5 Blind",
    "pyram": "Pyraminx",
    "skewb": "Skewb",
    "clock": "Clock",
    "minx": "Megaminx",
    "sq1": "Square-1",
    "234": "2+3+4 Relay",
    #* separator --------------------------------
    "333ft":"3x3 Feet"
}

AO5 = [
    "222",
    "333",
    "444",
    "555",
    "333oh",
    "pyram",
    "skewb",
    "clock",
    "minx",
    "sq1",
]

MO3 = ["666", "777","333fm","333bf","444bf","555bf"]
BO1 = ["333mbf"]
def category_attempts(cid): #catgory id
    if cid in MO3:
        return 3
    else:
        return 5

#CATEGORIES_SORTED = ["222","333","444","555","666","777","333oh","333bld","333bf","333mbf","333fm","444bld","444bf","pyram","skewb","clock","minx","sq1","234"]
CATEGORIES_SORTED = ["333","222","444","555","333oh","pyram","skewb","clock","minx","sq1","666","777","333bf","444bf","234","555bf"]
# 333, 222, 444, 555, 333oh, pyram, skewb, clock, minx, sq1, 666, 777, 333bld, 234

POINTS = [
    100,
    80,
    60,
    50,
    45,
    40,
    36,
    32,
    29,
    26,
    24,
    22,
    20,
    18,
    16,
    15,
    14,
    13,
    12,
    11,
    10,
    9,
    8,
    7,
    6,
    5,
    4,
    3,
    2,
    1,
]
