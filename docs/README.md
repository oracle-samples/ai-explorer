# Oracle AI Microservices Sandbox - Documentation

## Description

This directory contains the documentation for the the [**Oracle AI Microservices Sandbox**](https://github.com/oracle-samples/oaim-sandbox).

## Getting Started - Documentation

The **Oracle AI Microservices Sandbox** documentation is powered by [Hugo](https://gohugo.io/) using the [Relearn](https://github.com/McShelby/hugo-theme-relearn) theme.

To contribute to the documentation, install [Hugo](https://gohugo.io/installation/). Installation instructions vary per Operating System.

From the `docs` directory:

1. Download the [Relearn](https://github.com/McShelby/hugo-theme-relearn) theme
   ```bash
   mkdir -p themes/relearn
   wget -qO- $(curl -s https://api.github.com/repos/McShelby/hugo-theme-relearn/releases/latest \
      | grep "tarball_url" | awk -F'"' '{print $4}') \
      | tar --exclude='*/exampleSite' -xz -C themes/relearn --strip-components=1
   ```

1. Start Hugo: `hugo serve`

This will serve the documentation on `http://localhost:1313/oaim-sandbox/` for review.
