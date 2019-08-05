# Summer of code
Repository for summer job work at The National Library of Norway 2019

The repository mostly contains code for OOS (out-of-scope) handling, with a few adjacent tasks (Doc2Vec, language detection, etc...)

Additional files for language detection using machine learning are available [here](https://drive.google.com/open?id=1Om7PGu_auqUMncnj1tIikawcy_9tnytj). These files are not used, but exist for later reference if needed.

The main file is server.py, which when run provides two services:
- URL Norvegica detection ("/url").
    - Takes in a single URL, and gives a score of how Norwegian the website is (on a scale from 0 to 1), as well as details for the prediction.
- Language detection ("/language")
    - Does only the language detection part of the URL service.
    - Takes in text or raw html, and uses [cld2](https://github.com/CLD2Owners/cld2) to produce language predictions.
    
There is also a Dockerfile which will load the relevant files, install necessary packages and run server.py

Example outputs:
<details>
<summary>URL</summary>
<p>
Input:

```json
{"url": "https://nb.no"}
```
</p>
<p>
Output:

```json
{
    "original_url": "https://nb.no",
    "redirect_url": "https://www.nb.no/",
    "ip": "158.39.129.53",
    "geo": "NO",
    "domain": "no",
    "html_lang": "nb-NO",
    "content_language": null,
    "norwegian_version": {
        "url": "https://www.nb.no/",
        "scheme": "already_no",
        "ip_match": 4
    },
    "language": {
        "is_reliable": true,
        "text_bytes_found": 3206,
        "details": {
            "0": {
                "language_name": "NORWEGIAN",
                "language_code": "no",
                "percent": 97,
                "score": 792
            },
            "1": {
                "language_name": "ENGLISH",
                "language_code": "en",
                "percent": 2,
                "score": 1323
            },
            "2": {
                "language_name": "Unknown",
                "language_code": "un",
                "percent": 0,
                "score": 0
            }
        },
        "norwegian_score": 0.999999961478861
    },
    "regex": {
        "postal": {
            "unique": 0,
            "total": 0
        },
        "phone": {
            "unique": 0,
            "total": 0
        },
        "county": {
            "unique": 1,
            "total": 2
        },
        "name": {
            "unique": 0,
            "total": 0
        },
        "norway": {
            "unique": 2,
            "total": 4
        },
        "kroner": {
            "unique": 0,
            "total": 0
        },
        "email": {
            "unique": 1,
            "total": 1
        }
    },
    "norvegica_score": 0.9558058238157995,
    "text": "Gå til innhold Gå til menyen Søk i nettbiblioteket Søk i redaksjonelt innhold Hjem Om samlingen..."
}
```
</p>
</details>


<details>
<summary>Language</summary>
<p>
Input: 

```json
{"text": "Du må ikke sitte trygt i ditt hjem og si: Det er sørgelig, stakkars dem! Du må ikke tåle så inderlig vel den urett som ikke rammer dig selv! Du må ikke sitte trygt i ditt hjem og si: Det er sørgelig, stakkars dem! Du må ikke tåle så inderlig vel den urett som ikke rammer dig selv! Jeg roper med siste pust av min stemme: Du har ikke lov til å gå der og glemme!"}
```
</p>
<p>
Output:

```json
{
    "is_reliable": true,
    "text_bytes_found": 365,
    "details": {
        "0": {
            "language_name": "NORWEGIAN",
            "language_code": "no",
            "percent": 99,
            "score": 793
        },
        "1": {
            "language_name": "Unknown",
            "language_code": "un",
            "percent": 0,
            "score": 0
        },
        "2": {
            "language_name": "Unknown",
            "language_code": "un",
            "percent": 0,
            "score": 0
        }
    }
}
```
</p>
</details>
