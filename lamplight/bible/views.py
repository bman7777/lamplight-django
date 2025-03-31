from django.shortcuts import render, HttpResponse
#import logging
#logger = logging.getLogger(__name__)

def books(request):
    #logger.debug(f"Request data: {request.GET}")
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"Request headers: {request.headers}")
    return HttpResponse("<p>Hello world</p>", content_type='text/html')
