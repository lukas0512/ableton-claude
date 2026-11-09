# MOTRA 1.4.0

MOTRA is the chosen product name: motivo + track. The native window and sidebar now use MOTRA, with the signature “Ideias em movimento”. Installer output is `MOTRA-1.4.0-arm64.pkg`; the optional disk image uses the same naming.

The app retains the existing bundle identifier, executable and `~/Music/Ableton Claude` data location so saved profiles, authentication and references remain available. No bridge or music-engine change is included in this branding release.

Local validation: Swift compilation and native self-test passed, installer built, and the installed app passed code-signature verification. The existing frozen backend from 1.3.0 was reused. The native app was then exercised against Live through a separate MOTRA soundtrack project.

The marketing project is editable in `marketing/loop-to-track`. Its soundtrack is composed through the native app and ClaudeBridge in a separate Live set. Musical listening approval remains with the producer.
