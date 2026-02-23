"""Utility to test connectivity"""
import urllib.request
import urllib.error

def check_url_connectivity(url):
    """
    Check the connectivity of a URL by performing GET and POST requests.
    """
    try:
        # Test GET
        urllib.request.urlopen(url, timeout=2)

        # Test POST (empty data)
        req = urllib.request.Request(url, data=b'', method='POST')
        urllib.request.urlopen(req, timeout=2)

        return True

    except urllib.error.HTTPError as e:
        # Server responded with an HTTP error code (like 406, 404, 500, etc.)
        # This means the server is reachable, so return True
        return True
    except (urllib.error.URLError, OSError) as e:
        # Skip URLs that are unreachable or timeout
        return False
