import re

import glom
from django.http import JsonResponse


def search(request):
    query = request.GET.get("q")
    if query:
        # check if the query is a specific bible resource
        verse_matches = re.findall(
            r"(\d*)[ ]*([\w\s]+)[ ]*(\d+)\:?(\d*)", query.strip()
        )
        if verse_matches and (len(verse_matches[0]) == 4):
            verse_matches = verse_matches[0]

            # normalize the string to avoid spelling/spacing inconsistencies
            book = (verse_matches[0] + " " + verse_matches[1]).strip()
            book = " ".join(word.capitalize() for word in book.split(" "))

            chapter = verse_matches[2] if verse_matches[2] else "1"

            # todo: return a list of verses if asking for the whole chapter
            verse = verse_matches[3] if verse_matches[3] else "1"

            return JsonResponse(
                {
                    "data": [
                        {
                            "book": book,
                            "chapter": int(chapter),
                            "verse": int(verse),
                            "text": "shdkf",
                        }
                    ]
                },
                status=201,
            )

    return JsonResponse(
        {"data": [{"book": "Matthew", "chapter": 8, "verse": 28, "text": "shdkf"}]},
        status=201,
    )
