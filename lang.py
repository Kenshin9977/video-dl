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
    destination = enum.auto()
    start = enum.auto()
    end = enum.auto()
    subtitles = enum.auto()
    quality = enum.auto()
    framerate = enum.auto()
    vcodec = enum.auto()
    acodec = enum.auto()
    audio_only = enum.auto()
    song_only = enum.auto()
    song_only_tooltip = enum.auto()
    cookies = enum.auto()
    cookies_tooltip = enum.auto()
    dl_button = enum.auto()
    destination_folder = enum.auto()
    language = enum.auto()
    indices_selected = enum.auto()
    cookies_none = enum.auto()

    # Main window properties
    width = enum.auto()

    # Main window status
    dl_cancel = enum.auto()
    error = enum.auto()
    dl_error = enum.auto()
    dl_finish = enum.auto()
    invalid_output_path = enum.auto()
    theme = enum.auto()
    playlist_not_found = enum.auto()
    unsupported_url = enum.auto()
    file_in_use = enum.auto()
    no_encoder = enum.auto()

    # Progress window
    download = enum.auto()
    process = enum.auto()
    update = enum.auto()
    ff_remux = enum.auto()
    ff_reencode = enum.auto()
    starting = enum.auto()
    speed = enum.auto()
    cancel_button = enum.auto()

    # Error window
    permission_error_windows = enum.auto()
    permission_error_unix = enum.auto()


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

    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        pass
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
        GuiField.process: {
            Language.english: "Processing",
            Language.french: "Traitement",
            Language.german: "Echtzeitverarbeitung",
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
            Language.english: "Target quality",
            Language.french: "Qualité cible",
            Language.german: "Qualität ziel",
        },
        GuiField.framerate: {
            Language.english: "Target fps",
            Language.french: "IPS cible",
            Language.german: "Bildfrequenz ziel",
        },
        GuiField.vcodec: {
            Language.english: "Video codec",
            Language.french: "Codec vidéo",
            Language.german: "Codec video",
        },
        GuiField.acodec: {
            Language.english: "Audio codec",
            Language.french: "Codec audio",
            Language.german: "Codec audio",
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
        GuiField.cookies: {
            Language.english: "Cookies",
            Language.french: "Cookies",
            Language.german: "Cookies",
        },
        GuiField.cookies_tooltip: {
            Language.english: (
                "Browser from which to retrieve cookies. Useful if the media "
                "requires you to be connected to an account to access it."
            ),
            Language.french: (
                "Navigateur depuis lequel récupérer les cookies."
                " Utile dans le cas où pour accéder au média il faut être "
                "connecté à un compte."
            ),
            Language.german: (
                "Browser, von dem Cookies abgerufen werden sollen. Nützlich, "
                "wenn das Medium erfordert, dass Sie mit einem Konto verbunden"
                " sind, um darauf zuzugreifen."
            ),
        },
        GuiField.dl_button: {
            Language.english: "Download",
            Language.french: "Télécharger",
            Language.german: "Herunterladen",
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
        GuiField.cookies_none: {
            Language.english: "None",
            Language.french: "Aucun",
            Language.german: "None",
        },
        GuiField.dl_cancel: {
            Language.english: "Download cancelled.",
            Language.french: "Téléchargement annulé.",
            Language.german: "Herunterladen abgebrochen.",
        },
        GuiField.error: {
            Language.english: "Error: ",
            Language.french: "Erreur : ",
            Language.german: "Software-Fehler: ",
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
        GuiField.invalid_output_path: {
            Language.english: "Select a valid output path.",
            Language.french: "Indiquez un dossier de destination valide.",
            Language.german: "Wählen Sie einen gültigen Ausgabepfad.",
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
        GuiField.starting: {
            Language.english: "Starting",
            Language.french: "Démarrage",
            Language.german: "Starte",
        },
        GuiField.speed: {
            # Add a space at the end of the message if
            # the language requires one before a colon
            Language.english: "Speed",
            Language.french: "Vitesse ",
            Language.german: "Geschwindigkeit",
        },
        GuiField.cancel_button: {
            Language.english: "Cancel",
            Language.french: "Annuler",
            Language.german: "Abbrechen",
        },
        GuiField.update: {
            Language.english: "Update",
            Language.french: "Mise à jour",
            Language.german: "Aktualisierung",
        },
        GuiField.unsupported_url: {
            Language.english: "Unsupported URL",
            Language.french: "URL non gérée",
            Language.german: "Nicht unterstützte URL",
        },
        GuiField.file_in_use: {
            Language.english: "File already in use",
            Language.french: "Fichier en cours d'utilisation",
            Language.german: "Datei wird bereits verwendet",
        },
        GuiField.no_encoder: {
            Language.english: "No capable encoder found",
            Language.french: "Aucun encodeur apte trouvé",
            Language.german: "Kein fähiger Encoder gefunden",
        },
        GuiField.width: {
            Language.english: 420,
            Language.french: 440,
            Language.german: 480,
        },
        GuiField.theme: {
            Language.english: "Dark mode",
            Language.french: "Mode sombre",
            Language.german: "Dunkelmodus",
        },
        GuiField.playlist_not_found: {
            Language.english: (
                "Playlist not found, probably private. Try setting the Cookies"
            ),
            Language.french: (
                "Playlist introuvable, proablement privée. Essayez de régler "
                "l'option Cookies"
            ),
            Language.german: (
                "Wiedergabeliste nicht gefunden, wahrscheinlich privat. "
                "Versuchen Sie die Cookies zu setzen"
            ),
        },
        GuiField.permission_error_windows: {
            Language.english: (
                "Video-dl has been executed in a folder where it does not have"
                " write permission. Please restart the application as "
                "administrator or move the executable"
            ),
            Language.french: (
                "Video-dl a été exécuté dans un dossier où il n'a pas les "
                "droits d'écriture. Veuillez relancer l'applicaton en tant "
                "qu'adminisatrateur ou déplacez l'exécutable"
            ),
            Language.german: (
                "Video-dl wurde in einem Ordner ausgeführt, in dem es keine "
                "Schreibrechte hat. Bitte starten Sie die Anwendung als "
                "Administrator neu oder verschieben Sie die ausführbare Datei."
            ),
        },
        GuiField.permission_error_unix: {
            Language.english: (
                "Video-dl has been executed in a folder where it has no write "
                "permission. Please restart the application with sudo or move "
                "the executable"
            ),
            Language.french: (
                "Video-dl a été exécuté dans un dossier où il n'a pas les "
                "droits d'écriture. Veuillez relancer l'applicaton avec sudo"
                " ou déplacez l'exécutable"
            ),
            Language.german: (
                "Video-dl wurde in einem Ordner ausgeführt, in dem es keine "
                "Schreibrechte hat. Bitte starten Sie die Anwendung mit sudo "
                "neu oder verschieben Sie die Datei."
            ),
        },
    }
    return ui_text[field][_current_language]


_available_languages = {
    Language.english: "English",
    Language.french: "Français",
    Language.german: "Deutsch",
}

_language_from_name = {
    name: lang for lang, name in _available_languages.items()
}


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
