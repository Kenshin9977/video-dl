POI_CATEGORIES = {
        'poi_highlight': 'Highlight',
}
NON_SKIPPABLE_CATEGORIES = {
    **POI_CATEGORIES,
    'chapter': 'Chapter',
}
CATEGORIES = {
    'sponsor': 'Sponsor',
    'intro': 'Intermission/Intro Animation',
    'outro': 'Endcards/Credits',
    'selfpromo': 'Unpaid/Self Promotion',
    'preview': 'Preview/Recap',
    'filler': 'Filler Tangent',
    'interaction': 'Interaction Reminder',
    'music_offtopic': 'Non-Music Section',
    **NON_SKIPPABLE_CATEGORIES,
}