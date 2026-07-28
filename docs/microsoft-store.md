# video-dl and the Microsoft Store

Short version: **do not lead with this channel.** WinGet and Chocolatey are the
right homes for this tool. The Store is possible, and this file records what it
would take and what the actual risk is, so the decision is made on facts rather
than on a vague sense that it is off limits.

## Why it is a different question from WinGet and Chocolatey

Those two are rule-based. Meet the manifest requirements and a human sanity check
and you are in; yt-dlp itself and several of its GUIs already are.

Store certification is **discretionary**. Reviewers apply the content policies
with judgement, and media downloaders are a category that has historically drawn
more of it. There is precedent in both directions: yt-dlg has listed on the Store,
and other downloaders have been pulled over the years.

So the realistic outcome is not "banned", it is "uncertain, and it can be undone
later by someone else's judgement call". That is a poor foundation for a primary
distribution channel and a fine one for a secondary one.

## What would actually decide it

Nothing about the code, and everything about the listing. Two things matter:

- **No DRM circumvention.** yt-dlp does not break DRM and neither does this. That
  is the line with legal weight, and it is already on the right side of it.
- **The listing describes the tool, not a use case.** A description that
  advertises ripping a named streaming service invites the rejection. The
  descriptions in `packaging/` are written this way already and should be reused
  verbatim rather than rewritten to be punchier for a store page.

## If you do submit it

The Store takes plain EXE installers hosted by you: no MSIX, no repackaging.

| Field | Value |
| --- | --- |
| App type | EXE |
| Package URL | `https://github.com/Kenshin9977/video-dl/releases/download/v<version>/video-dl-windows-setup.exe` |
| Architecture | x64 |
| Installer parameters | `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` |
| Languages | `en-us`, `fr-fr` |

Requirements this already meets: every PE file is signed by the build workflow
with a certificate chaining to the Microsoft Trusted Root Program, the Inno setup
is standalone rather than a downloader stub, and GitHub release assets are
immutable per tag, which satisfies "the binary must not change after submission".

The one that needs the switch above: the install must show no UI. Inno's default
is a wizard, so silence is not optional.

## Two things to settle first

**Self-updating.** tufup updates the app in place, so a Store install would move
to a version the Store did not certify. Either accept that, as most Win32 Store
apps do, or build a Store variant with the updater off and let the Store be the
update channel.

**The bundled yt-dlp.** The portable build carries its own yt-dlp and ffmpeg.
That is fine, and it is worth stating plainly in the listing rather than leaving
a reviewer to discover it: an app that quietly ships another downloader inside
looks worse than one that says so.
