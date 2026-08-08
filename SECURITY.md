# Security Policy

## Scope and threat model

RestoreForge AI is a local desktop application. It has no server component, no
authentication, no network listener and no user accounts. It processes files
you already have, on hardware you already control.

That shape means the realistic security surface is small but not empty:

* **Setup downloads.** During installation the application fetches PyTorch from
  the official PyTorch wheel index and PyPI, and model weights from published
  GitHub release URLs. These are the only outbound requests the project makes.
* **Model weights.** Weights are `.pth` files loaded by PyTorch. They are
  downloaded from the upstream projects' official release URLs and size-checked
  before use.
* **Subprocess execution.** The application runs `ffmpeg`, `ffprobe`,
  `powershell` and the virtual environment's `python`. Paths you supply are
  passed as argument-list elements, never through a shell string.
* **The website.** A statically exported set of files. No database, no API
  routes, no user input reaching a server.

## Supported versions

The project is pre-1.0. Only the latest `main` receives fixes.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting on the repository's Security tab.
If that is unavailable, open a normal issue titled "Security contact request"
containing no technical detail, and a maintainer will arrange a private channel.

Please include:

* A description of the issue and why you believe it is a security problem
* Steps to reproduce
* The version or commit, your Windows version and GPU
* Any suggested fix

You can expect an acknowledgement within seven days and an assessment within
thirty. Because this is a volunteer project there is no guaranteed remediation
timeline, but credible reports will be prioritised over feature work.

## Out of scope

* The absence of a code-signing certificate on the source distribution
* Issues that require an attacker to already have local administrator rights
* Vulnerabilities in PyTorch, FFmpeg, NVIDIA drivers or Windows — please report
  those upstream
* Model output quality, artifacts or hallucinated detail, which are inherent
  properties of generative upscaling rather than security issues

## Good practice for users

* Obtain the source from the official repository only.
* Let setup download the model weights rather than sourcing `.pth` files from
  elsewhere. PyTorch checkpoints can execute code when loaded, so a weight file
  from an untrusted origin is a genuine risk.
* Keep your NVIDIA driver and Python installation current.
