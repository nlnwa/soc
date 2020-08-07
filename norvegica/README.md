# Norvegica
Package for norvegica detection for use on out of scope websites.

## Usage
The main file is server.py, which when run provides two services:
- URL Norvegica detection ("/url").
    - Takes a single `url`, and gives a score of how Norwegian the website is (on a scale from 0 to 1), as well as details for the prediction.
- Language detection ("/language")
    - Does only the language detection part of the URL service.
    - Takes in `text` and/or `raw_html`, or `url`, and uses [cld2](https://github.com/CLD2Owners/cld2) to produce language predictions.

There is also a Dockerfile which will load the relevant files, install necessary packages and run server.py

## Result description
Descriptions of the fields returned by the "/url" service. The "/language" service returns only the `language` part without `norwegian_score`
- `original_url`: The original input URL
- `redirect_url`: The resulting URL after redirect
- `ip`: The IP of the website
- `geo`: The geolocation of the website as determined by GeoIP2
- `domain`: The domain of the website
- `html_lang`: Lang tag of the website HTML
- `content_language`: Content-Language from HTTP header
- `norwegian_version`: Information about possible Norwegian version
    - `url`: The URL of the Norwegian version
    - `ip_match`: The number of matching IPv4 bytes (0-4) between `ip` and the ip of the Norwegian version.
    - `scheme`: Method of discovery, can be one of (in order of estimated strength):
        - `already_no`: The website's domain is already .no, this is quite uninteresting and is therefore returned only if no other matches are found.
        - `href-hreflang-rel`: Link that follows [the format recommended by Google](https://support.google.com/webmasters/answer/189077?hl=en) to specify alternate language versions
        - `href-norway-full`: Link that contains text with only "Norway"/"Norwegian" in any language
        - `replace`: Found by replacing domain with .no
        - `href-hreflang`: Other link with hreflang tag.
        - `href-norway-partial`: Link that contains text with "Norway"/"Norwegian" in any language, but also other text
        - `href-lang`: Link with lang tag
        - `href-norway-link`: Link where URL contains "Norway"/"Norwegian" in any language
        - `no_match`: No Norwegian version was found
- `language`: Language information produced by cld2. Apart from `norwegian_score` this is also the result from the "/language" service
    - `norwegian_score`: A calculated score of how Norwegian the text is on a scale from 0 to 1
    - `is_reliable`: Whether or not the language detection considers the prediction to be reliable
    - `text_bytes_found`: Number of text bytes found by the language detection
    - `details`: Details about the language prediction, gives information about the top three languages
        - `0`, `1`, `2`: The language rank
            - `language_name`: Name of language
            - `language_code`: Language code
            - `percent`: The estimated percentage of the text that is this language
            - `score`: A score of how confident the prediction is
- `regex`: Regex information. For each expression the number of `unique` and `total` matches is given
    - `postal`: Postal codes, e.g. `8624 Mo i Rana`
    - `phone`: Phone numbers, e.g. `+47 23 27 60 00`
    - `county`: Norwegian counties, e.g. `Nordland`
    - `name`: Typical Norwegian names, made by combining the most common first and last names in Norway (from [SSB](https://www.ssb.no/)), e.g. `Jan Hansen`
    - `norway`: "Norway"/"Norwegian" in any language.
    - `kroner`: Any number + kr, e.g. `420 kr`
    - `email`: Any email that ends with .no, e.g. `nb@nb.no`
- `norvegica_score`: Final score of how 'Norwegian' the website seems to be
- `text`: The extracted text from the website

### Example outputs:
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
        "scheme": "href-hreflang-rel",
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
    "norvegica_score": 0.9628372756716147,
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
