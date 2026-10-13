# Interactive diagrams

Standalone, explorable HTML views of voxbridge (built with Archify). Open the
`.html` files in a browser: pan, zoom, search, follow a path, and click a node's
`SRC` badge to jump to the exact code file and lines it was drawn from.

| View | What it answers |
|---|---|
| [voxbridge-architecture.html](voxbridge-architecture.html) | What the system is made of and how the parts connect |
| [voxbridge-flow.html](voxbridge-flow.html) | One voice turn (STT → dialogue → TTS), end to end |

Each `.html` is rebuilt from its `*.candidate.json` with Archify; edit the JSON, not the HTML.
