import os
import sys
import json
import base64
import webview


# Συνάρτηση για να βρίσκει τα paths των αρχείων (απαραίτητο για το .exe)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class Api:
    def get_library(self):
        """Διαβάζει αυτόματα όλα τα .json από τον τοπικό φάκελο 'library'."""
        library_data = {}
        # Ο φάκελος 'library' πρέπει να είναι στον ίδιο κατάλογο με το exe/script
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        library_path = os.path.join(exe_dir, 'library')

        if not os.path.exists(library_path):
            try:
                os.makedirs(library_path)
            except:
                pass
            return {}

        for filename in os.listdir(library_path):
            if filename.endswith('.json'):
                file_path = os.path.join(library_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        comp_id = filename.replace('.json', '')
                        library_data[comp_id] = json.load(f)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        return library_data

    def export_to_folder(self, data):
        try:
            lobby_id = data.get('lobbyId', 'default_lobby')
            main_config = data.get('config')
            files = data.get('files', [])
            library_configs = data.get('libraryConfigs', [])

            result = window.create_file_dialog(webview.FOLDER_DIALOG)
            if not result:
                return "Η εξαγωγή ακυρώθηκε."

            base_path = result[0]

            # 1. Δημιουργία φακέλου Lobby
            lobby_path = os.path.join(base_path, lobby_id)
            if not os.path.exists(lobby_path):
                os.makedirs(lobby_path)

            # Αποθήκευση του κεντρικού config.json μέσα στο lobby folder
            with open(os.path.join(lobby_path, 'config.json'), 'w', encoding='utf-8') as f:
                # Αν το main_config είναι string (από το UI), το γράφουμε απευθείας
                f.write(main_config)

            # 2. Δημιουργία φακέλων για τα Components (Library)
            for lib in library_configs:
                lib_id = lib['id']
                lib_content = lib['config']

                # Μετατροπή σε JSON string με σωστά ελληνικά (ensure_ascii=False)
                lib_json_str = json.dumps(lib_content, indent=2, ensure_ascii=False) if isinstance(lib_content, (
                dict, list)) else lib_content

                lib_folder_path = os.path.join(base_path, lib_id)
                if not os.path.exists(lib_folder_path):
                    os.makedirs(lib_folder_path)

                with open(os.path.join(lib_folder_path, 'config.json'), 'w', encoding='utf-8') as f:
                    f.write(lib_json_str)

            # 3. Αποθήκευση εικόνων ΜΕΣΑ ΣΤΟΝ ΦΑΚΕΛΟ ΤΟΥ LOBBY
            for file_info in files:
                try:
                    header, data_b64 = file_info['data'].split(',', 1)
                    file_data = base64.b64decode(data_b64)

                    with open(os.path.join(lobby_path, file_info['name']), 'wb') as f:
                        f.write(file_data)
                except:
                    continue

            return f"Επιτυχής εξαγωγή!\nΤα αρχεία αποθηκεύτηκαν στο: {base_path}"

        except Exception as e:
            return f"Σφάλμα: {str(e)}"


api = Api()
window = webview.create_window(
    'Nexto Gaming Config Builder',
    resource_path('index.html'),
    js_api=api,
    width=1650,
    height=1000,
    resizable=True
)

if __name__ == '__main__':
    # Το debug=True βοηθάει να βλέπεις σφάλματα στην κονσόλα αν κάτι δεν πάει καλά
    webview.start(debug=True)