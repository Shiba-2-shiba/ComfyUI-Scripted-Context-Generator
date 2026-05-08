"""Profiles used by the compositional action generator.

These tables are deliberately data-like. Keep expansion-oriented location
profiles here so `action_generator.py` can focus on parsing, slot assembly, and
rendering behavior.
"""

DEFAULT_DAILY_LIFE_TAGS = {"school", "office", "urban", "domestic", "suburban", "resort", "japanese"}

TAG_BASED_DAILY_LIFE_PROFILES = {
    "school": {
        "purpose": ["study", "wait", "rest"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before class starts", "during a lunch break", "after school"],
        "weather": ["sunlight reaching the windows", "rain tapping against the glass"],
        "obstacle": ["forgot", "delay"],
    },
    "office": {
        "purpose": ["work", "wait", "commute"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["before the meeting begins", "during a short break", "near the end of the workday"],
        "weather": ["the city light reflecting through the glass", "rain streaks showing on the windows"],
        "obstacle": ["delay", "forgot", "luggage"],
    },
    "urban": {
        "purpose": ["shop", "wait", "commute", "rest"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "stranger", "crowd", "acquaintance"],
        "time": ["in the late afternoon", "during the evening rush", "on the way home"],
        "weather": ["a cool breeze moving through the street", "light rain lingering in the air"],
        "obstacle": ["delay", "luggage", "spill"],
    },
    "domestic": {
        "purpose": ["rest", "work", "wait"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["in the quiet part of the morning", "late in the evening", "before heading to bed"],
        "weather": ["soft daylight coming through the window", "the room holding onto the rainy weather outside"],
        "obstacle": ["spill", "forgot"],
    },
    "suburban": {
        "purpose": ["commute", "shop", "rest", "wait"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "stranger", "acquaintance"],
        "time": ["before the next errand", "on the way back home", "as the neighborhood quiets down"],
        "weather": ["wind moving past the houses", "the road still damp from rain"],
        "obstacle": ["delay", "luggage", "forgot"],
    },
    "resort": {
        "purpose": ["rest", "wait", "shop"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance", "crowd"],
        "time": ["during a slow afternoon", "just before sunset", "after a long walk"],
        "weather": ["warm air drifting through the space", "sea light reflecting nearby"],
        "obstacle": ["luggage", "delay"],
    },
    "japanese": {
        "purpose": ["rest", "wait", "work"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["in the stillness of the morning", "late in the afternoon", "as the day starts winding down"],
        "weather": ["soft wind moving through the garden", "rain settling over the eaves"],
        "obstacle": ["wind", "forgot"],
    },
}

LOC_SPECIFIC_DAILY_LIFE_PROFILES = {
    "commuter_transport": {
        "purpose": ["commute", "wait"],
        "social_distance": ["stranger", "crowd", "alone"],
        "time": ["during the morning rush", "between train stops", "on the ride home"],
        "weather": ["the windows fogged from the weather outside", "rainwater shaking loose at each stop"],
        "obstacle": ["delay", "luggage"],
    },
    "street_cafe": {
        "purpose": ["rest", "wait", "shop"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["while the afternoon slows down", "before meeting someone", "between errands"],
        "weather": ["a light breeze stirring the parasol", "sunlight shifting across the table"],
        "obstacle": ["spill", "delay"],
    },
    "cozy_bookstore": {
        "purpose": ["shop", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before the shop closes", "during a rainy afternoon", "while the store stays hushed"],
        "weather": ["rain muttering beyond the front window", "dusty sunlight slipping between the shelves"],
    },
    "shopping_mall_atrium": {
        "purpose": ["shop", "wait", "rest"],
        "social_distance": ["crowd", "stranger", "acquaintance"],
        "time": ["during the weekend rush", "between store visits", "after finishing most of the shopping"],
        "weather": ["light from the skylight shifting overhead", "the glass roof holding back the gray sky"],
        "obstacle": ["luggage", "delay"],
    },
    "fashion_boutique": {
        "purpose": ["shop", "wait"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["while deciding on one last item", "between trips to the fitting room", "before checking out"],
        "obstacle": ["delay", "luggage"],
    },
    "school_library": {
        "purpose": ["study", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["during the last quiet hour", "between classes", "after the rain drives everyone indoors"],
        "weather": ["soft rain dimming the windows", "late daylight stretching over the tables"],
    },
    "office_elevator": {
        "purpose": ["commute", "wait", "work"],
        "social_distance": ["stranger", "acquaintance"],
        "time": ["between floors on a busy morning", "after a long meeting", "on the way back down"],
        "obstacle": ["delay", "forgot", "luggage"],
    },
    "modern_office": {
        "purpose": ["work", "wait", "rest"],
        "social_distance": ["alone", "acquaintance", "crowd"],
        "time": ["before the inbox fills up", "in the middle of the afternoon slump", "after most people have left"],
        "obstacle": ["delay", "forgot"],
    },
    "boardroom": {
        "purpose": ["work", "wait"],
        "social_distance": ["acquaintance", "stranger"],
        "time": ["before the agenda starts", "while the discussion drags on", "as the meeting wraps up"],
        "obstacle": ["delay", "forgot"],
    },
    "bedroom_boudoir": {
        "purpose": ["rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before getting ready to leave", "after finally coming home", "before sleeping"],
        "weather": ["rain-muted light on the curtains", "soft sunlight at the edge of the room"],
    },
    "messy_kitchen": {
        "purpose": ["work", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["while getting breakfast ready", "between chores", "after dinner is over"],
        "obstacle": ["spill", "forgot"],
    },
    "rainy_bus_stop": {
        "purpose": ["wait", "commute"],
        "social_distance": ["alone", "stranger"],
        "time": ["before the next bus arrives", "on the way home after dark", "during a long delay"],
        "weather": ["rain drumming on the shelter roof", "cold wind slipping under the awning"],
        "obstacle": ["delay", "wind"],
    },
    "suburban_neighborhood": {
        "purpose": ["commute", "rest", "shop"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["between errands", "on the walk back home", "as the sunset spreads over the houses"],
        "weather": ["wind moving along the hedges", "warm evening light over the street"],
    },
}

LOCATION_CONTEXT_HINTS = [
    (
        ("platform", "terminal", "ticket_gate", "transport", "crosswalk"),
        {
            "anchors": ["near the route display", "by the edge of the walkway", "close to the next exit"],
            "gaze_target": ["glancing toward the next arrival", "watching the flow of people ahead"],
        },
    ),
    (
        ("store", "aisle", "arcade", "market", "bakery", "restaurant", "food_court", "cinema_lobby", "game_arcade"),
        {
            "anchors": ["between the nearby displays", "by the counter", "along the busiest part of the aisle"],
            "gaze_target": ["checking what is available nearby", "looking over the next thing to choose"],
        },
    ),
    (
        ("library", "hallway", "courtyard", "cafeteria", "clubroom", "community_center"),
        {
            "anchors": ["near the side of the room", "along the quieter part of the space", "by the nearest table"],
            "gaze_target": ["looking toward the part of the room she needs", "checking the people moving around her"],
        },
    ),
    (
        ("balcony", "entryway", "laundry", "playground"),
        {
            "anchors": ["near the railing", "close to the doorway", "beside the open space in front of her"],
            "gaze_target": ["looking out over the space for a moment", "watching what is happening just ahead"],
        },
    ),
]
