import enum
import locale


class Language(enum.Enum):
    english = enum.auto()
    french = enum.auto()
    german = enum.auto()


class GuiField(enum.Enum):
    # Main window static text
    incorrect_timestamp = enum.auto()
    invalid_url = enum.auto()
    link = enum.auto()
    is_playlist = enum.auto()
    playlist_items = enum.auto()
    start = enum.auto()
    end = enum.auto()
    subtitles = enum.auto()
    quality = enum.auto()
    quality_tooltip = enum.auto()
    framerate = enum.auto()
    framerate_tooltip = enum.auto()
    vcodec = enum.auto()
    acodec = enum.auto()
    audio_only = enum.auto()
    song_only = enum.auto()
    song_only_tooltip = enum.auto()
    destination_folder = enum.auto()
    language = enum.auto()
    indices_selected = enum.auto()
    advanced = enum.auto()
    nle_ready = enum.auto()
    nle_ready_tooltip = enum.auto()
    will_remux = enum.auto()
    will_reencode = enum.auto()
    vcodec_auto_tooltip = enum.auto()
    acodec_auto_tooltip = enum.auto()
    vcodec_original_tooltip = enum.auto()
    acodec_original_tooltip = enum.auto()
    original = enum.auto()
    original_tooltip = enum.auto()
    original_video_placeholder = enum.auto()
    original_audio_placeholder = enum.auto()
    open_folder = enum.auto()
    login_from = enum.auto()
    login_from_tooltip = enum.auto()
    login_from_none = enum.auto()

    # Main window properties
    width = enum.auto()

    # Main window status
    dl_cancel = enum.auto()
    dl_error = enum.auto()
    dl_finish = enum.auto()
    theme = enum.auto()
    playlist_not_found = enum.auto()
    unsupported_url = enum.auto()
    no_encoder = enum.auto()

    # Progress window
    download = enum.auto()
    process = enum.auto()
    ff_remux = enum.auto()
    ff_reencode = enum.auto()
    cancel_button = enum.auto()

    # Preparation status
    preparing = enum.auto()
    extracting_cookies = enum.auto()
    fetching_info = enum.auto()
    solving_js = enum.auto()

    # Queue
    queue_button_tooltip = enum.auto()
    queue_dialog_title = enum.auto()
    queue_dialog_hint = enum.auto()
    queue_dialog_ok = enum.auto()
    queue_dialog_clear = enum.auto()
    queue_invalid_urls = enum.auto()


def _get_language() -> Language:
    """
    Tries to determine the system language, fallbacks to english.
    """
    # This dictionary maps the language of a locale to its associated enum
    lang_map = {
        "en": Language.english,
        "fr": Language.french,
        "de": Language.german,
    }

    import contextlib

    with contextlib.suppress(Exception):
        locale.setlocale(locale.LC_ALL, "")
    system_language = locale.getlocale()[0]

    if system_language is None:
        return Language.english

    for available_language in lang_map:
        if available_language in system_language:
            return lang_map[available_language]

    return Language.english


_current_language = _get_language()


def get_text(field: GuiField) -> str:
    ui_text = {
        GuiField.incorrect_timestamp: {
            Language.english: "Invalid timestamps",
            Language.french: "Temps saisis invalides",
            Language.german: "Ungültiger Zeitstempel",
        },
        GuiField.invalid_url: {
            Language.english: "Enter a valid URL",
            Language.french: "Entrer une URL valide",
            Language.german: "Gültige URL eingeben",
        },
        GuiField.link: {
            Language.english: "Link",
            Language.french: "Lien",
            Language.german: "Link",
        },
        GuiField.is_playlist: {
            Language.english: "Playlist",
            Language.french: "Playlist",
            Language.german: "Wiedergabeliste",
        },
        GuiField.playlist_items: {
            Language.english: "Indices",
            Language.french: "Index",
            Language.german: "Indizes",
        },
        GuiField.download: {
            Language.english: "Download",
            Language.french: "Téléchargement",
            Language.german: "Herunterladen",
        },
        GuiField.process: {
            Language.english: "Processing",
            Language.french: "Traitement",
            Language.german: "Echtzeitverarbeitung",
        },
        GuiField.start: {
            Language.english: "Start",
            Language.french: "Début",
            Language.german: "Anfang",
        },
        GuiField.end: {
            Language.english: "End",
            Language.french: "Fin",
            Language.german: "Ende",
        },
        GuiField.subtitles: {
            Language.english: "Subtitles",
            Language.french: "Sous-titres",
            Language.german: "Untertitel",
        },
        GuiField.quality: {
            Language.english: "Max quality",
            Language.french: "Qualité max",
            Language.german: "Max. Qualität",
        },
        GuiField.quality_tooltip: {
            Language.english: "Best available quality up to this resolution",
            Language.french: "Meilleure qualité disponible jusqu'à cette résolution",
            Language.german: "Beste verfügbare Qualität bis zu dieser Auflösung",
        },
        GuiField.framerate: {
            Language.english: "Max fps",
            Language.french: "IPS max",
            Language.german: "Max. Bildfrequenz",
        },
        GuiField.framerate_tooltip: {
            Language.english: "Best available framerate up to this value",
            Language.french: "Meilleure fréquence d'images disponible jusqu'à cette valeur",
            Language.german: "Beste verfügbare Bildfrequenz bis zu diesem Wert",
        },
        GuiField.vcodec: {
            Language.english: "Target video codec",
            Language.french: "Codec vidéo cible",
            Language.german: "Ziel-Videocodec",
        },
        GuiField.acodec: {
            Language.english: "Target audio codec",
            Language.french: "Codec audio cible",
            Language.german: "Ziel-Audiocodec",
        },
        GuiField.audio_only: {
            Language.english: "Audio only",
            Language.french: "Audio seul",
            Language.german: "Nur Audio",
        },
        GuiField.song_only: {
            Language.english: "Song only",
            Language.french: "Musique seulement",
            Language.german: "Nur Lied",
        },
        GuiField.song_only_tooltip: {
            Language.english: "Uses SponsorBlock to discard any non musical section",  # noqa
            Language.french: "Utilise SponsorBlock pour retirer toutes les parties non musicales",  # noqa
            Language.german: "Verwendet SponsorBlock, um alle nicht musikalischen Abschnitte zu verwerfen",  # noqa
        },
        GuiField.destination_folder: {
            Language.english: "Destination folder",
            Language.french: "Dossier de destination",
            Language.german: "Zielordner",
        },
        GuiField.language: {
            Language.english: "Language",
            Language.french: "Langue",
            Language.german: "Sprache",
        },
        GuiField.indices_selected: {
            Language.english: "Indices selected",
            Language.french: "Index sélectionnés",
            Language.german: "Indizes ausgewählt",
        },
        GuiField.advanced: {
            Language.english: "Advanced",
            Language.french: "Avancé",
            Language.german: "Erweitert",
        },
        GuiField.nle_ready: {
            Language.english: "NLE Ready",
            Language.french: "Prêt pour montage",
            Language.german: "NLE-kompatibel",
        },
        GuiField.nle_ready_tooltip: {
            Language.english: (
                "Ensures the video is compatible with editing software (DaVinci Resolve, Premiere, etc.)"
            ),
            Language.french: (
                "S'assure que la vidéo est compatible avec les logiciels de montage (DaVinci Resolve, Premiere, etc.)"
            ),
            Language.german: (
                "Stellt sicher, dass das Video mit Schnittsoftware kompatibel ist (DaVinci Resolve, Premiere, etc.)"
            ),
        },
        GuiField.will_remux: {
            Language.english: "Remux only (fast, lossless)",
            Language.french: "Remux uniquement (rapide, sans perte)",
            Language.german: "Nur Remux (schnell, verlustfrei)",
        },
        GuiField.will_reencode: {
            Language.english: "Re-encoding required (slower)",
            Language.french: "Réencodage nécessaire (plus lent)",
            Language.german: "Neukodierung erforderlich (langsamer)",
        },
        GuiField.vcodec_auto_tooltip: {
            Language.english: (
                "Auto: keeps the original codec if NLE-compatible (h264, h265, ProRes), otherwise re-encodes to h264"
            ),
            Language.french: (
                "Auto : conserve le codec d'origine s'il est compatible"
                " NLE (h264, h265, ProRes), sinon réencode en h264"
            ),
            Language.german: (
                "Auto: behält den Original-Codec bei, wenn NLE-kompatibel"
                " (h264, h265, ProRes), sonst Neukodierung in h264"
            ),
        },
        GuiField.acodec_auto_tooltip: {
            Language.english: (
                "Auto: keeps the original codec if NLE-compatible (AAC, MP3), otherwise re-encodes to AAC"
            ),
            Language.french: (
                "Auto : conserve le codec d'origine s'il est compatible NLE (AAC, MP3), sinon réencode en AAC"
            ),
            Language.german: (
                "Auto: behält den Original-Codec bei, wenn NLE-kompatibel (AAC, MP3), sonst Neukodierung in AAC"
            ),
        },
        GuiField.vcodec_original_tooltip: {
            Language.english: ("Original: keeps the original codec, remuxes to mp4 container (fast, no re-encoding)"),
            Language.french: (
                "Original : conserve le codec d'origine, remux vers un conteneur mp4 (rapide, sans réencodage)"
            ),
            Language.german: (
                "Original: behält den Original-Codec bei, Remux in mp4-Container (schnell, keine Neukodierung)"
            ),
        },
        GuiField.acodec_original_tooltip: {
            Language.english: ("Original: keeps the audio codec as-is, no re-encoding"),
            Language.french: ("Original : conserve le codec audio tel quel, sans réencodage"),
            Language.german: ("Original: behält den Audio-Codec bei, ohne Neukodierung"),
        },
        GuiField.original: {
            Language.english: "Original",
            Language.french: "Original",
            Language.german: "Original",
        },
        GuiField.original_tooltip: {
            Language.english: "Keep original codecs — select specific streams from the source",
            Language.french: "Conserver les codecs d'origine — sélectionner les flux de la source",
            Language.german: "Original-Codecs beibehalten — Quellstreams auswählen",
        },
        GuiField.original_video_placeholder: {
            Language.english: "Video stream",
            Language.french: "Flux vidéo",
            Language.german: "Videostream",
        },
        GuiField.original_audio_placeholder: {
            Language.english: "Audio stream",
            Language.french: "Flux audio",
            Language.german: "Audiostream",
        },
        GuiField.open_folder: {
            Language.english: "Open folder",
            Language.french: "Ouvrir le dossier",
            Language.german: "Ordner öffnen",
        },
        GuiField.login_from: {
            Language.english: "Login from",
            Language.french: "Connexion depuis",
            Language.german: "Anmeldung von",
        },
        GuiField.login_from_tooltip: {
            Language.english: (
                "Browser from which to retrieve login cookies. Useful if the"
                " media requires you to be logged in to access it."
            ),
            Language.french: (
                "Navigateur depuis lequel récupérer les cookies de connexion."
                " Utile dans le cas où pour accéder au média il faut être"
                " connecté à un compte."
            ),
            Language.german: (
                "Browser, von dem Login-Cookies abgerufen werden sollen."
                " Nützlich, wenn das Medium erfordert, dass Sie angemeldet"
                " sind, um darauf zuzugreifen."
            ),
        },
        GuiField.login_from_none: {
            Language.english: "None",
            Language.french: "Aucun",
            Language.german: "Keine",
        },
        GuiField.dl_cancel: {
            Language.english: "Download cancelled.",
            Language.french: "Téléchargement annulé.",
            Language.german: "Herunterladen abgebrochen.",
        },
        GuiField.dl_error: {
            Language.english: "An error has occurred.",
            Language.french: "Une erreur s'est produite.",
            Language.german: "Ein Fehler ist aufgetreten.",
        },
        GuiField.dl_finish: {
            Language.english: "Download finished.",
            Language.french: "Téléchargement terminé.",
            Language.german: "Herunterladen abgeschlossen.",
        },
        GuiField.ff_remux: {
            Language.english: "Remuxing",
            Language.french: "Remuxage",
            Language.german: "Remuxen",
        },
        GuiField.ff_reencode: {
            Language.english: "Re-encoding",
            Language.french: "Réencodage",
            Language.german: "Neukodierung",
        },
        GuiField.cancel_button: {
            Language.english: "Cancel",
            Language.french: "Annuler",
            Language.german: "Abbrechen",
        },
        GuiField.unsupported_url: {
            Language.english: "Unsupported URL",
            Language.french: "URL non gérée",
            Language.german: "Nicht unterstützte URL",
        },
        GuiField.no_encoder: {
            Language.english: "No capable encoder found",
            Language.french: "Aucun encodeur apte trouvé",
            Language.german: "Kein fähiger Encoder gefunden",
        },
        GuiField.preparing: {
            Language.english: "Preparing download...",
            Language.french: "Préparation du téléchargement...",
            Language.german: "Download wird vorbereitet...",
        },
        GuiField.extracting_cookies: {
            Language.english: "Extracting cookies...",
            Language.french: "Extraction des cookies...",
            Language.german: "Cookies werden extrahiert...",
        },
        GuiField.fetching_info: {
            Language.english: "Fetching video info...",
            Language.french: "Récupération des infos...",
            Language.german: "Video-Infos werden abgerufen...",
        },
        GuiField.solving_js: {
            Language.english: "Solving JS challenge...",
            Language.french: "Résolution du challenge JS...",
            Language.german: "JS-Challenge wird gelöst...",
        },
        GuiField.queue_button_tooltip: {
            Language.english: "Add URLs to queue",
            Language.french: "Ajouter des URLs à la file",
            Language.german: "URLs zur Warteschlange hinzufügen",
        },
        GuiField.queue_dialog_title: {
            Language.english: "Download queue",
            Language.french: "File de téléchargement",
            Language.german: "Download-Warteschlange",
        },
        GuiField.queue_dialog_hint: {
            Language.english: "One URL per line",
            Language.french: "Une URL par ligne",
            Language.german: "Eine URL pro Zeile",
        },
        GuiField.queue_dialog_ok: {
            Language.english: "OK",
            Language.french: "OK",
            Language.german: "OK",
        },
        GuiField.queue_dialog_clear: {
            Language.english: "Clear",
            Language.french: "Vider",
            Language.german: "Leeren",
        },
        GuiField.queue_invalid_urls: {
            Language.english: "Some URLs were invalid and removed",
            Language.french: "Certaines URLs invalides ont été retirées",
            Language.german: "Einige ungültige URLs wurden entfernt",
        },
        GuiField.width: {
            Language.english: 530,
            Language.french: 550,
            Language.german: 570,
        },
        GuiField.theme: {
            Language.english: "Dark mode",
            Language.french: "Mode sombre",
            Language.german: "Dunkelmodus",
        },
        GuiField.playlist_not_found: {
            Language.english: ("Playlist not found, probably private. Try setting the Cookies"),
            Language.french: ("Playlist introuvable, proablement privée. Essayez de régler l'option Cookies"),
            Language.german: (
                "Wiedergabeliste nicht gefunden, wahrscheinlich privat. Versuchen Sie die Cookies zu setzen"
            ),
        },
    }
    return ui_text[field][_current_language]  # type: ignore[index]


_available_languages = {
    Language.english: "\U0001f1ec\U0001f1e7",
    Language.french: "\U0001f1eb\U0001f1f7",
    Language.german: "\U0001f1e9\U0001f1ea",
}

_language_from_name = {name: lang for lang, name in _available_languages.items()}


def get_available_languages_name() -> list[str]:
    """
    Returns a list of all the available languages in a human-readable form.
    """
    return list(_available_languages.values())


def get_current_language_name() -> str:
    """
    Get the name of the current language.
    """
    return _available_languages[_current_language]


def set_current_language(name: str) -> None:
    """
    Set the current language.

    "name" must be available, else no changes will be made.
    """
    if name not in _language_from_name:
        return
    global _current_language
    _current_language = _language_from_name[name]
