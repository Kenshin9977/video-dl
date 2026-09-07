# Publishing video-dl to WinGet and Chocolatey

The two channels get different artifacts, and the reason is worth knowing before
you change either.

`installer/video-dl.iss` sets `PrivilegesRequired=lowest` and installs into
`{localappdata}\Programs`. Chocolatey runs **elevated**. Put those together and
`choco install` would install into the administrator's profile, where the person
who typed the command cannot see it.

| | Artifact | Scope | Who updates it |
| --- | --- | --- | --- |
| WinGet | `video-dl-windows-setup.exe` | user, declared in the manifest | tufup, in the app |
| Chocolatey | `video-dl-windows.exe` | machine | `choco upgrade` |

---

## Is this the sort of thing these channels accept?

Yes, with plenty of precedent. yt-dlp itself is on both
([`yt-dlp.yt-dlp`](https://winstall.app/apps/yt-dlp.yt-dlp) on WinGet, `yt-dlp`
on Chocolatey), and so are several GUIs for it, including
[`dsymbol.yt-dlp-gui`](https://winstall.app/apps/dsymbol.yt-dlp-gui) and
`jely2002.youtube-dl-gui`.

Two things keep it that way, and both are worth not breaking:

- **The listing describes the tool, not a use case.** The manifests say what the
  program does and leave what may be downloaded to the site's terms and to local
  law. A listing that advertises ripping a particular streaming service is the
  kind that gets pulled.
- **No DRM circumvention.** yt-dlp does not break DRM and neither does this. That
  is the line that actually matters legally, and it is already on the right side
  of it.

The Microsoft Store is a different matter and is not covered here. Its review is
discretionary in a way these two are not.

---

## Chocolatey

### One time

1. Create an account at <https://community.chocolatey.org/account/Register>.
2. Copy your API key from <https://community.chocolatey.org/account>.
3. Add it as the repository secret `CHOCOLATEY_API_KEY`.

### Every release

Automatic. The `chocolatey` job fills the version, URL and SHA-256 of the
artifact the release job just published, downloads it to confirm the checksum
matches reality, packs and pushes.

Without the secret the job still packs and only skips the push.

### Expect questions on the first submission

Moderation is thorough, and a PyInstaller bundle carrying its own yt-dlp and
ffmpeg attracts more of it than most. `tools/VERIFICATION.txt` says plainly what
is inside and where it comes from, which is what they are asking for. Answer
promptly and it goes through; a rejected version number cannot be reused.

### Testing locally

```powershell
choco pack packaging/chocolatey/video-dl.nuspec --out packaging/chocolatey
choco install video-dl --source packaging/chocolatey --version <version> -y
choco uninstall video-dl -y
```

Substitute the placeholders in `chocolateyinstall.ps1` first.

---

## WinGet

### The first submission is manual

`wingetcreate update` needs an existing manifest. Create the first one:

1. Fork <https://github.com/microsoft/winget-pkgs>.

2. Fill in the three manifests in `packaging/winget/`, replacing every
   `<FILL:...>`:

   - `<FILL:VERSION>` the release version
   - `<FILL:URL>` the release asset URL of `video-dl-windows-setup.exe`
   - `<FILL:SHA256>` its SHA-256, uppercase

3. Validate, then actually install from it:

   ```powershell
   winget validate --manifest packaging\winget
   winget install --manifest packaging\winget
   ```

   The second command is the one that matters. It proves the Inno silent switches
   and the `ProductCode` are right, which is what a first PR usually bounces on.

4. Copy them into your fork under
   `manifests/k/Kenshin9977/video-dl/<version>/` and open a pull request.

### The ProductCode

`{6F3A2C41-8B7D-4E29-9C15-video-dl-0001}_is1`, from the `AppId` in
`video-dl.iss` plus the `_is1` suffix Inno appends. It is how WinGet recognises
an existing install.

**If you ever change `AppId` in the .iss, this must change with it**, or WinGet
will stop seeing installs it made and start offering the package as new.

### Every release after that

Automatic once `WINGET_TOKEN` is set: a **classic** personal access token with
the `public_repo` scope. Fine-grained tokens cannot fork, and `wingetcreate`
needs to.

### One thing to watch

tufup updates the app in place, so WinGet may offer an upgrade to a version
already running. Normal for self-updating apps, and why the `ProductCode` is
declared.
