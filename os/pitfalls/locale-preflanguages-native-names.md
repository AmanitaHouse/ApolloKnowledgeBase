---
title: loc_PrefLanguages holds native names, not the LOCALE:Catalogs directory names
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [source-code, measured]
components: [libraries]
applies_to:
  core: "any"
  os: [apolloos-r10]
  mode: [os-friendly]
tags: [locale, localisation, catalogs, languages, help]
related: []
sources:
  - "ApolloOS-Port, workbench/libs/locale/initlocale.c (BuildPreferredLanguages, LanguagesOnDiskNames)"
  - "ApolloOS-Port, workbench/utilities/Help/main.c, commit b3765aa1 (2026-11-24)"
---

## Symptom

A program builds its own per-language path from the user's language, for
example `HELP:<language>/` or `PROGDIR:docs/<language>/`, next to the
catalogs in `LOCALE:Catalogs/german/`. Catalogs come up in the user's
language, but the program's own files are never found and it falls back
to English.

## Cause

On ApolloOS (AROS locale.library), `struct Locale` `loc_PrefLanguages[]`
holds the **native** language names that the `.language` files report:
`deutsch`, `nederlands`, `français`, `italiano`, `español`, `polski`,
`português`. Prefs/Locale stores the **on-disk** names (`german`, `dutch`,
`french`, ...) and `OpenCatalog()` maps native to on-disk internally
(`LanguagesOnDiskNames`), which is not public. Code that puts
`loc_PrefLanguages[i]` into a path therefore looks for `HELP:deutsch`
while the directories, like `LOCALE:Catalogs/`, are named `german`.
Several native names are not ASCII.

## Wrong

```c
struct Locale *loc = OpenLocale(NULL);
snprintf(path, sizeof(path), "HELP:%s/%s.guide",
         loc->loc_PrefLanguages[0], name);      /* HELP:deutsch/... */
```

## Right

```c
/* map the native names of the languages you ship files for */
static const char *const map[][2] = {
    { "deutsch", "german" }, { "nederlands", "dutch" },
    { "fran\xe7" "ais", "french" }, { "italiano", "italian" },
    { "espa\xf1ol", "spanish" }, { "polski", "polish" },
    { "portugu\xea" "s", "portuguese" }, { NULL, NULL } };

static CONST_STRPTR disk_name(CONST_STRPTR native)
{
    int i;
    for (i = 0; map[i][0]; i++)
        if (Stricmp(native, map[i][0]) == 0)
            return map[i][1];
    return native;                              /* try it as it is */
}
```

Split hex escapes before a following hex letter (`"fran\xe7" "ais"`):
`"fran\xe7ais"` is one out-of-range escape.

## Detection

Set a language in Prefs/Locale, reboot, and check that the program's own
per-language files (not only its catalog) appear. Print
`loc_PrefLanguages[0]` from a test program.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| `loc_PrefLanguages` is built from the native names; catalogs use `LanguagesOnDiskNames` | (SRC) workbench/libs/locale/initlocale.c | any | Read |
| Utilities/Help opened the English guide with German set, the German guide after mapping `deutsch` to `german`; same for the six other languages | (M) 2026-11-24 | Core 12856 | ApolloOS R9.9 dev card, locale.prefs per language, reboot, Help Copy, screen captured |
