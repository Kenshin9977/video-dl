import enum
import locale


class Language(enum.Enum):
    english = enum.auto()
    french = enum.auto()
    german = enum.auto()


class GuiField(enum.Enum):
    # Main window static text
    link = enum.auto()
    destination = enum.auto()
    start = enum.auto()
    end = enum.auto()
    quality = enum.auto()
    framerate = enum.auto()
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


global current_language


def _get_language() -> Language:
    """
    Tries to determine the system language, fallbacks to english.
    """
    global current_language

    # This dictionary maps the language of a locale to its associated enum
    lang_map = {
        "en": Language.english,
        "fr": Language.french,
        "de": Language.german
    }

    locale.setlocale(locale.LC_ALL, "")
    system_language = locale.getdefaultlocale()[0]

    if (system_language is None):
        return Language.english

    for available_language in lang_map.keys():
        if(available_language in system_language):
            return lang_map[available_language]

    return Language.english


current_language = _get_language()


def get_text(field: GuiField) -> str:
    ui_text = {
        GuiField.link: {
            Language.english: "Link",
            Language.french: "Lien",
            Language.german: "Link"
        },
        GuiField.destination: {
            Language.english: "Destination folder",
            Language.french: "Dossier de destination",
            Language.german: "Zielordner"
        },
        GuiField.start: {
            Language.english: "Start",
            Language.french: "Début",
            Language.german: "Anfang"
        },
        GuiField.end: {
            Language.english: "End",
            Language.french: "Fin",
            Language.german: "Ende"
        },
        GuiField.quality: {
            Language.english: "Maximum quality",
            Language.french: "Qualité maximale",
            Language.german: "Maximale Qualität"
        },
        GuiField.framerate: {
            Language.english: "Maximum framerate",
            Language.french: "Nombre d'image par seconde maximum",
            Language.german: "Maximale Bildfrequenz"
        },
        GuiField.audio_only: {
            Language.english: "Audio only",
            Language.french: "Audio seul",
            Language.german: "Nur Audio"
        },
        GuiField.cookies: {
            Language.english: "Use cookies from the selected browser",
            Language.french: "Utiliser les cookies du navigateur selectionné",
            Language.german: "Benutze Cookies des ausgewählten Webbrowsers"
        },
        GuiField.dl_button: {
            Language.english: "Download",
            Language.french: "Télécharger",
            Language.german: "Herunterladen"
        },
        GuiField.dl_cancel: {
            Language.english: "Download cancelled.",
            Language.french: "Téléchargement annulé.",
            Language.german: "Herunterladen abgebrochen."
        },
        GuiField.dl_unsupported_url: {
            Language.english: "Unsupported URL.",
            Language.french: "URL non supportée.",
            Language.german: "URL nicht unterstützt."
        },
        GuiField.dl_error: {
            Language.english: "An error has occurred.",
            Language.french: "Une erreur s'est produite.",
            Language.german: "Ein Fehler ist aufgetreten."
        },
        GuiField.dl_finish: {
            Language.english: "Download finished.",
            Language.french: "Téléchargement terminé.",
            Language.german: "Herunterladen abgeschlossen."
        },
        GuiField.missing_output: {
            Language.english: "Select an output path.",
            Language.french: "Indiquez un dossier de destination.",
            Language.german: "Wähle einen Zielordner."
        },
        GuiField.ff_remux: {
            Language.english: "Remuxing",
            Language.french: "Remuxage",
            Language.german: "Remuxen"
        },
        GuiField.ff_reencode: {
            Language.english: "Re-encoding",
            Language.french: "Réencodage",
            Language.german: "Neukodierung"
        },
        GuiField.ff_starting: {
            Language.english: "Starting",
            Language.french: "Démarrage",
            Language.german: "Starte"
        },
        GuiField.ff_speed: { 
            # Add a space at the end of the message if 
            # the language requires one before a colon
            Language.english: "Speed",
            Language.french: "Vitesse ",
            Language.german: "Geschwindigkeit"
        }
    }
    global current_language
    return ui_text[field][current_language]
