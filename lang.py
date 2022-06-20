import enum
import locale
from typing import List


class Language(enum.Enum):
    english = enum.auto()
    french = enum.auto()
    german = enum.auto()


class GuiField(enum.Enum):
    # Main window static text
    incorrect_timestamp = enum.auto()
    link = enum.auto()
    is_playlist = enum.auto()
    playlist_items = enum.auto()
    download = enum.auto()
    destination = enum.auto()
    start = enum.auto()
    end = enum.auto()
    subtitles = enum.auto()
    quality = enum.auto()
    framerate = enum.auto()
    vcodec = enum.auto()
    acodec = enum.auto()
    audio_only = enum.auto()
    cookies = enum.auto()
    dl_button = enum.auto()

    # Main window status
    dl_cancel = enum.auto()
    dl_unsupported_url = enum.auto()
    dl_error = enum.auto()
    dl_finish = enum.auto()
    missing_output = enum.auto()

    # Progress window
    ff_remux = enum.auto()
    ff_reencode = enum.auto()
    ff_starting = enum.auto()
    ff_speed = enum.auto()
    cancel_button = enum.auto()


def _get_language() -> Language:
    """
    Tries to determine the system language, fallbacks to english.
    """
    # This dictionary maps the language of a locale to its associated enum
    lang_map = {"en": Language.english, "fr": Language.french, "de": Language.german}

    locale.setlocale(locale.LC_ALL, "")
    system_language = locale.getdefaultlocale()[0]

    if system_language is None:
        return Language.english

    for available_language in lang_map.keys():
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
        GuiField.destination: {
            Language.english: "Destination folder",
            Language.french: "Dossier de destination",
            Language.german: "Zielordner",
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
            Language.english: "Maximum quality",
            Language.french: "Qualité maximale",
            Language.german: "Maximale Qualität",
        },
        GuiField.framerate: {
            Language.english: "Maximum framerate",
            Language.french: "Fréquence d'images par seconde maximum",
            Language.german: "Maximale Bildfrequenz",
        },
        GuiField.vcodec: {
            Language.english: "Video codec",
            Language.french: "Codec vidéo",
            Language.german: "Codec für video",
        },
        GuiField.acodec: {
            Language.english: "Audio only codec",
            Language.french: "Codec audio",
            Language.german: "Codec für audio",
        },
        GuiField.audio_only: {
            Language.english: "Audio only",
            Language.french: "Audio seul",
            Language.german: "Nur Audio",
        },
        GuiField.cookies: {
            Language.english: "Use cookies from the selected browser",
            Language.french: "Utiliser les cookies du navigateur selectionné",
            Language.german: "Benutze Cookies des ausgewählten Webbrowsers",
        },
        GuiField.dl_button: {
            Language.english: "Download",
            Language.french: "Télécharger",
            Language.german: "Herunterladen",
        },
        GuiField.dl_cancel: {
            Language.english: "Download cancelled.",
            Language.french: "Téléchargement annulé.",
            Language.german: "Herunterladen abgebrochen.",
        },
        GuiField.dl_unsupported_url: {
            Language.english: "Unsupported URL.",
            Language.french: "URL non supportée.",
            Language.german: "URL nicht unterstützt.",
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
        GuiField.missing_output: {
            Language.english: "Select an output path.",
            Language.french: "Indiquez un dossier de destination.",
            Language.german: "Wähle einen Zielordner.",
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
        GuiField.ff_starting: {
            Language.english: "Starting",
            Language.french: "Démarrage",
            Language.german: "Starte",
        },
        GuiField.ff_speed: {
            # Add a space at the end of the message if
            # the language requires one before a colon
            Language.english: "Speed",
            Language.french: "Vitesse",
            Language.german: "Geschwindigkeit",
        },
        GuiField.cancel_button: {
            Language.english: "Cancel",
            Language.french: "Annuler",
            Language.german: "",
        },
    }
    return ui_text[field][_current_language]


_available_languages = {
    Language.english: "English",
    Language.french: "Français",
    Language.german: "Deutsch",
}

_language_from_name = {name: lang for lang, name in _available_languages.items()}


def get_available_languages_name() -> List[str]:
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
    return
