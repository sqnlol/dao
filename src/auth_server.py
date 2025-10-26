import socketserver
import http.server
import urllib.parse
import threading
import sys
import time

# Globalna zmienna do przechowywania wyników OpenID
STEAM_AUTH_RESULT = None

# Zmienna do przechowywania instancji serwera HTTP
current_server = None

class SteamOpenIDHandler(http.server.BaseHTTPRequestHandler):
    """
    Obsługuje żądanie zwrotne OpenID od Steam.
    """
    def do_GET(self):
        global STEAM_AUTH_RESULT, current_server
        
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'openid.identity' in query_params:
            # Pomyślna autoryzacja
            identity_url = query_params['openid.identity'][0]
            steam_id = identity_url.split('/')[-1]
            
            STEAM_AUTH_RESULT = {'steam_id': steam_id, 'success': True}

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            # Treść HTML
            html_content = (
                "<html><head><title>Zalogowano!</title>"
                # Ponowna próba automatycznego zamknięcia
                "<script>window.onload = function() { setTimeout(function() { window.close(); }, 100); };</script>"
                "</head>"
                "<body>"
                "<h1>✅ Logowanie udane!</h1>"
                "<p>Twoje konto Steam zostało uwierzytelnione. Proszę wrócić do aplikacji. Jeśli karta się nie zamknie, zamknij ją ręcznie.</p>"
                "</body></html>"
            )
            self.wfile.write(html_content.encode('utf-8'))
            
            # 🛑 KLUCZOWA ZMIANA: Zamykamy serwer, do którego referencja została przekazana.
            # Zapewnia to, że po wysłaniu odpowiedzi, serwer natychmiast próbuje się zamknąć.
            if current_server:
                 # Zamknięcie w nowym wątku, aby nie blokować odpowiedzi 200
                 threading.Thread(target=current_server.shutdown).start()
        
        else:
            # Błąd autoryzacji
            STEAM_AUTH_RESULT = {'success': False, 'error': 'Błąd: Steam nie zwrócił tożsamości. Logowanie nieudane.'}
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Autoryzacja nieudana.".encode('utf-8'))
            
            # Zamykamy serwer
            if current_server:
                 threading.Thread(target=current_server.shutdown).start()


def run_auth_server(host, port):
    """
    Uruchamia serwer HTTP w osobnym wątku.
    """
    global STEAM_AUTH_RESULT, current_server
    STEAM_AUTH_RESULT = None

    server_address = (host, port)
    
    try:
        # 🛑 POWRÓT DO PODSTAWOWEJ IMPLEMENTACJI BEZ ThreadingMixIn
        httpd = socketserver.TCPServer(server_address, SteamOpenIDHandler, bind_and_activate=False)
        httpd.allow_reuse_address = True
        httpd.server_bind()
        httpd.server_activate()
    except OSError as e:
        if "Address already in use" in str(e):
             STEAM_AUTH_RESULT = {'success': False, 'error': 'Błąd serwera: Port 8080 jest już używany. Zamknij inne programy.', 'steam_id': None}
             return None
        raise
    
    # Przechowujemy referencję globalnie
    current_server = httpd 

    # Uruchamiamy serve_forever
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    
    return httpd