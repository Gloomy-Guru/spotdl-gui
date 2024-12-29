import sys
import logging
import requests
import subprocess
import os
import wget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QVBoxLayout, 
                             QWidget, QTableWidgetItem, QPushButton, QHeaderView, 
                             QMessageBox, QLabel, QTextEdit, QSplitter, QLineEdit)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import os
from dotenv import load_dotenv
import re
import spotdl

def download_track(url):
    subprocess.run(['spotdl', url])
def get_playlist_tracks(access_token, playlist_id):
    BASE_URL = "https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    url = BASE_URL.format(playlist_id=playlist_id)
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        tracks = []
        for item in data.get('items', []):
            track = item.get('track', {})
            track_details = {
                "track_name": track.get("name"),
                "artist_name": ", ".join(artist.get("name") for artist in track.get("artists", [])),
                "album_name": track.get("album", {}).get("name"),
                "length_ms": track.get("duration_ms"),
                "cover_url": track.get("album", {}).get("images", [{}])[0].get("url"),
                "track_url": track.get("external_urls", {}).get("spotify")
            }
            tracks.append(track_details)
        return tracks
    else:
        self.log_message(f"Failed to fetch playlist tracks: {response.status_code}", 'error')
        return []

def export_id(url):
    match = re.search(r"(?<=playlist\/)[\w\d]+", url)
    if match:
        return match.group(0)
    else:
        raise ValueError("the url is not correct")

def get_spotify_access_token():
    client_id = os.getenv("client_id")
    client_secret = os.getenv("client_secret")

    if not client_id or not client_secret:
        raise ValueError("Client ID and Client Secret must be set as environment variables.")

    # make the request
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        access_token = response.json().get("access_token")
        return access_token
    else:
        raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")

def format_duration(duration_ms):
    """Convert milliseconds to human-readable format."""
    total_seconds = duration_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

class SpotifyPlaylistViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initMain()
    
    def initMain(self):

        # window infos
        self.setWindowTitle('Spotify Playlist Viewer')
        self.setGeometry(100, 100, 1400, 800)

        main_splitter = QSplitter(Qt.Vertical)

        # setting layouts
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Type to search...")

        # search bar functionallity
        self.search_bar.setClearButtonEnabled(True)
        main_layout.addWidget(self.search_bar)
        self.search_bar.returnPressed.connect(self.searched)

        # create table
        self.table = QTableWidget()
        main_layout.addWidget(self.table)
        
        # configure table
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Cover', 'Track', 'Artist', 'Album', 'Length', 'Download'])

        # Set column widths
        self.table.setColumnWidth(0, 100)  # Cover column
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Track name
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Artist
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Album
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        # create log disp
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFixedHeight(200)
        main_layout.addWidget(self.log_display)

        self.setCentralWidget(central_widget)

    def fetch_tracks(self, tracks):
        self.table.setRowCount(len(tracks))

        for row, track in enumerate(tracks):
            # Track Name
            track_name = QTableWidgetItem(track.get("track_name", "N/A"))
            track_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 1, track_name)
            
            # Artist Name
            artist_name = QTableWidgetItem(track.get("artist_name", "N/A"))
            artist_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 2, artist_name)
            
            # Album Name
            album_name = QTableWidgetItem(track.get("album_name", "N/A"))
            album_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 3, album_name)
            
            # Track Length (Formatted)
            length = QTableWidgetItem(format_duration(track.get("length_ms", 0)))
            length.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, length)
            
            # Download Button
            download_btn = QPushButton("Download")
            download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
            """)
            download_btn.clicked.connect(lambda checked, url=track.get("track_url"): download_track(url))
            self.table.setCellWidget(row, 5, download_btn)
    
    def searched(self):
        search_input = self.search_bar.text()
        self.fetch_tracks(get_playlist_tracks(get_spotify_access_token(), export_id(search_input)))

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Arial', 10))  # Optional: Set application-wide font
    app.setStyle('Fusion')  # Set fusion style for a modern look
    
    viewer = SpotifyPlaylistViewer()
    viewer.show()
    
    try:
        sys.exit(app.exec_())
    except SystemExit:
        print("Closing application...")

if __name__ == "__main__":
    main()

