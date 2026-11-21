# Security Policy

## Supported versions

Only the latest release of the `jayasree` npm package (and the `master` branch it is cut from) is
supported. Fixes are released as a new version; older versions are not patched.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.** Report it privately through GitHub:
on this repository, **Security -> Advisories -> Report a vulnerability**. Include what you found,
how to reproduce it, and the version or commit it affects.

This is a small, volunteer-run project. You will get an acknowledgement as soon as the maintainer
can manage it - usually within a few days - and a fix or a clear decision after that. Please give
us reasonable time before disclosing publicly; we are happy to credit you in the release notes.

## What is in scope

- **The JS runtime** (`js/`, published as `jayasree`): for example script injection through the
  text it is given or the data files it loads, or anything that would run in a visitor's browser.
- **The build tooling** (`python/`, `tools/`): for example unsafe handling of file paths or of
  untrusted font or data files.
- **The CI, release and deploy workflows** (`.github/workflows/`) and the supply chain around
  them: for example a way to publish or deploy without review.

## What is not

- A letter that is the wrong shape, a stroke in the wrong order or a wobbly animation: that is a
  bug, not a vulnerability - please use the issue templates.
- Vulnerabilities in dependencies that do not affect this project; Dependabot tracks those.

The stroke data is public and openly licensed (see [LICENSE-DATA](LICENSE-DATA)); there are no
secrets or personal data in this repository.
