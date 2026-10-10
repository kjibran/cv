# Icon licences

The icons in icons.json are SVG paths taken from two open icon sets.

| Icons | Source | Licence |
|---|---|---|
| orcid, scholar, researchgate, scopus, wos, zenodo, cv | [Academicons](https://github.com/jpswalsh/academicons) 1.9.5 by James Walsh | SIL Open Font License 1.1 |
| mail, linkedin, github, portfolio, sun, moon | [Tabler Icons](https://github.com/tabler/tabler-icons) 3.49 | MIT |

Brand icons (ORCID, Google Scholar, LinkedIn, GitHub and so on) are trademarks of
their owners and are used only to link to the matching profile.

## Adding an icon

Each entry has a viewBox, a list of paths and a stroke flag:

```json
"name": {"viewBox": "0 0 24 24", "paths": [{"d": "M..."}], "stroke": false}
```

Use `"stroke": true` for outline icons (drawn with lines rather than filled).
Then use the name as `icon:` in data/profile.yaml.
